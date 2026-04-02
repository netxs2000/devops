import pytest
import uuid
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from devops_collector.models import Base, Organization, User, IdentityMapping, RawDataStaging
from devops_collector.plugins.wecom.worker import WeComWorker
from devops_collector.plugins.wecom.client import WeComClient

# --- Mock Data Definition ---

MOCK_DEPARTMENTS = [
    {"id": 1, "name": "总部", "parentid": 0, "order": 1},
    {"id": 10, "name": "研发中心", "parentid": 1, "order": 1},
    {"id": 20, "name": "测试部", "parentid": 10, "order": 2},
]

MOCK_DEPT_DETAILS = {
    "1": {"id": 1, "name": "总部", "parentid": 0, "department_leader": ["admin_wecom"]},
    "10": {"id": 10, "name": "研发中心", "parentid": 1, "department_leader": ["dev_lead"]},
    "20": {"id": 20, "name": "测试部", "parentid": 10, "department_leader": ["test_lead"]},
}

MOCK_USERS = {
    1: [{"userid": "admin_wecom", "name": "管理员", "email": "admin@tjhq.com", "department": [1]}],
    10: [{"userid": "dev_lead", "name": "研发主管", "email": "dev@tjhq.com", "department": [10]}],
    20: [
        {"userid": "test_lead", "name": "测试主管", "email": "test@tjhq.com", "department": [20]},
        {"userid": "tester1", "name": "测试员1", "email": "tester1@tjhq.com", "department": [20]},
    ],
}

# --- Database Setup ---

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    """提供干净的内存数据库会话。"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        # 预制一个存量用户，验证 OneID 自动对齐
        existing_user = User(
            global_user_id=uuid.uuid4(),
            full_name="测试员1号",
            primary_email="tester1@tjhq.com",  # 与 WeCom 侧 email 一致
            is_current=True,
            is_survivor=True
        )
        session.add(existing_user)
        session.commit()
        yield session
    finally:
        session.close()
        # SQLite 内存数据库在卸载时可能会遇到外键循环依赖问题，此处强制断开连接即可
        # Base.metadata.drop_all(bind=engine) # 在内存模式下，连接关闭即自动释放，直接 drop_all 可能触发 gkpj 错误

@pytest.fixture
def mock_wecom_client():
    """Mock 企业微信客户端，返回预定义的通讯录数据。"""
    client = MagicMock(spec=WeComClient)
    client.get_departments.return_value = MOCK_DEPARTMENTS
    client.get_department_detail.side_effect = lambda d_id: MOCK_DEPT_DETAILS.get(str(d_id)) or MOCK_DEPT_DETAILS.get(int(d_id))
    
    # 模拟 get_all_users 的去重逻辑
    all_users = []
    seen = set()
    for dept_id in MOCK_USERS:
        for u in MOCK_USERS[dept_id]:
            if u["userid"] not in seen:
                all_users.append(u)
                seen.add(u["userid"])
    client.get_all_users.return_value = all_users
    return client

@pytest.fixture
def wecom_worker(db_session, mock_wecom_client):
    """提供 WeComWorker 实例。"""
    return WeComWorker(
        session=db_session,
        client=mock_wecom_client,
        correlation_id="test-wecom-sync-001"
    )

# --- Integration Tests ---

def test_wecom_full_sync_flow(wecom_worker, db_session):
    """验证完整的 WeCom 同步链路：Staging -> Org -> Identity -> Realign。"""
    
    # 执行同步任务 (Full Scope)
    task = {"sync_scope": "full"}
    stats = wecom_worker.process_task(task)
    db_session.commit()

    # 1. 验证统计信息
    assert stats["departments"] == 3
    assert stats["users"] == 4
    assert stats["realigned"] == 3  # 3 个部门的负责人应该都被成功对齐了

    # 2. 验证 Staging 数据落盘 (MDM Golden Rule #1)
    staging_count = db_session.query(RawDataStaging).filter_by(source="wecom").count()
    # 3 depts + 4 users = 7 entries
    assert staging_count == 7

    # 3. 验证组织架构拓扑同步 (Phase 1)
    # 检查根节点
    root_org = db_session.query(Organization).filter_by(org_code="wecom_dept_1").first()
    assert root_org is not None
    assert root_org.org_name == "总部"
    assert root_org.org_level == 1
    assert root_org.source_system == "wecom"

    # 检查子节点层级
    dev_org = db_session.query(Organization).filter_by(org_code="wecom_dept_10").first()
    assert dev_org.parent_id == root_org.id
    assert dev_org.org_level == 2

    # 4. 验证人员身份对齐与 OneID 映射 (Phase 2)
    # 检查新建用户 (admin_wecom)
    admin_mapping = db_session.query(IdentityMapping).filter_by(
        source_system="wecom",
        external_user_id="admin_wecom"
    ).first()
    assert admin_mapping is not None
    assert admin_mapping.external_email == "admin@tjhq.com"
    
    # 检查存量对齐 (tester1)
    # tester1 在 db_session fixture 中已经预置了 User，应该实现了 OneID 关联
    tester1_mapping = db_session.query(IdentityMapping).filter_by(
        external_user_id="tester1"
    ).first()
    assert tester1_mapping is not None
    
    # 验证 mapping 是否指向了那个预置的 User
    existing_user = db_session.query(User).filter_by(primary_email="tester1@tjhq.com").first()
    assert tester1_mapping.global_user_id == existing_user.global_user_id

    # 5. 验证负责人延迟对齐自愈 (Phase 3)
    # 研发中心的负责人应该是 dev_lead，检查 Organization 上的 manager_user_id
    dev_lead_user = db_session.query(User).filter_by(primary_email="dev@tjhq.com").first()
    assert dev_org.manager_user_id == dev_lead_user.global_user_id
    assert dev_org.manager_raw_id == "dev_lead"

    print("\n[SUCCESS] WeCom full integration sync flow verified.")

if __name__ == "__main__":
    # 手动执行脚本环境下的简单验证
    pytest.main([__file__, "-v"])

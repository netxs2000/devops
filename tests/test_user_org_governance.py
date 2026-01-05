"""单元测试：用户、组织与身份治理模块

验证虚拟团队管理、增强型身份映射以及身份对齐治理引擎的核心逻辑。
使用 SQLite 物理文件数据库进行测试以保证多连接数据同步。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import uuid
import os

# 导入所有相关模型以确保 Base.metadata 完整
from devops_collector.models.base_models import Base, User, Organization, IdentityMapping, Team, TeamMember, Role, user_roles
import devops_collector.plugins.gitlab.models
import devops_collector.plugins.nexus.models
import devops_collector.plugins.jfrog.models
import devops_collector.plugins.zentao.models
import devops_collector.plugins.jenkins.models

from devops_portal.main import app
from devops_collector.auth.router import get_db
from scripts.run_identity_resolver import IdentityResolver

# --- 数据库配置 ---
DB_FILE = "./test_user_org.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 覆盖 FastAPI 的 get_db 依赖
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    """每个测试函数创建一个干净的数据库环境。"""
    # 物理删除旧文件确保 100% 干净
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except:
            pass
            
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    # 结束时不 drop，由下次运行前的 remove 处理，规避 SQLite 锁死 drop_all 的警告

# --- 1. 模型逻辑测试 ---

def test_virtual_team_relationships(db_session):
    """测试虚拟团队的模型关联关系。"""
    # 1. 创建 HR 组织和用户
    org = Organization(org_id="DEPT_研发", org_name="研发中心", is_current=True)
    user1 = User(global_user_id=uuid.uuid4(), full_name="张三", employee_id="1001", is_current=True)
    user2 = User(global_user_id=uuid.uuid4(), full_name="李四", employee_id="1002", is_current=True)
    db_session.add_all([org, user1, user2])
    db_session.flush()

    # 2. 创建虚拟团队
    team = Team(name="效能平台组", team_code="TEAM_EFF", leader_id=user1.global_user_id, org_id=org.org_id)
    db_session.add(team)
    db_session.flush()

    # 3. 添加成员与投入占比
    m1 = TeamMember(team_id=team.id, user_id=user1.global_user_id, role_code="LEADER", allocation_ratio=0.5)
    m2 = TeamMember(team_id=team.id, user_id=user2.global_user_id, role_code="MEMBER", allocation_ratio=1.0)
    db_session.add_all([m1, m2])
    db_session.commit()

    # 4. 验证关联
    queried_team = db_session.query(Team).filter_by(team_code="TEAM_EFF").first()
    assert len(queried_team.members) == 2
    assert queried_team.leader.full_name == "张三"
    
    # 验证用户维度的反向关联
    u2 = db_session.query(User).filter_by(employee_id="1002").first()
    assert len(u2.team_memberships) == 1
    assert u2.team_memberships[0].team.name == "效能平台组"

# --- 2. 身份治理引擎逻辑测试 ---

def test_identity_resolver_logic(db_session):
    """测试 scripts/run_identity_resolver.py 中的对齐算法。"""
    # 1. 准备 MDM 金数据
    user = User(
        global_user_id=uuid.uuid4(), 
        full_name="王五", 
        employee_id="W005", 
        username="wangwu",
        primary_email="wangwu@yourcompany.com",
        is_current=True
    )
    db_session.add(user)
    
    # 2. 准备待治理的外部帐号 (GitLab)
    mapping1 = IdentityMapping(
        source_system="gitlab",
        external_user_id="123",
        external_username="wangwu",  # Email 前缀匹配 username
        external_email="wangwu@gmail.com",
        mapping_status="PENDING"
    )
    
    mapping2 = IdentityMapping(
        source_system="gitlab",
        external_user_id="456",
        external_username="W5_Dev",
        external_email="W005@yourcompany.com", # Email 前缀匹配工号
        mapping_status="PENDING"
    )
    
    db_session.add_all([mapping1, mapping2])
    db_session.commit()

    # 3. 运行治理引擎
    resolver = IdentityResolver(db_session)
    resolver.run(dry_run=False)

    # 4. 验证结果
    # 验证 mapping1 (Email 前缀映射)
    m1 = db_session.query(IdentityMapping).filter_by(external_user_id="123").first()
    assert m1.global_user_id == user.global_user_id
    assert m1.mapping_status == "AUTO"
    assert m1.confidence_score == 0.8

    # 验证 mapping2 (Email 前缀映射)
    m2 = db_session.query(IdentityMapping).filter_by(external_user_id="456").first()
    assert m2.global_user_id == user.global_user_id
    assert m2.confidence_score == 0.8
    assert m2.mapping_status == "AUTO"

# --- 3. API 接口集成测试 ---

def test_api_user_full_profile(db_session):
    """测试获取用户全景画像接口。"""
    # 1. 构造测试数据
    u_id = uuid.uuid4()
    org = Organization(org_id="ORG_TEST", org_name="测试部", is_current=True)
    user = User(global_user_id=u_id, full_name="赵六", employee_id="R666", primary_email="zhao@ex.com", department_id=org.org_id, is_current=True)
    db_session.add_all([org, user])
    db_session.commit() # 物理库必须提交
    
    mapping = IdentityMapping(global_user_id=u_id, source_system="gitlab", external_user_id="git_666", external_email="zhao@ex.com", mapping_status="VERIFIED")
    team = Team(name="虚拟组X", team_code="X")
    db_session.add_all([mapping, team])
    db_session.commit()
    
    member = TeamMember(team_id=team.id, user_id=u_id, role_code="MEMBER", allocation_ratio=0.8)
    db_session.add(member)
    db_session.commit()

    # 2. 调用 API
    response = client.get(f"/admin/users/{u_id}")
    assert response.status_code == 200
    data = response.json()

    # 3. 验证聚合结果
    assert data["full_name"] == "赵六"
    assert data["department_name"] == "测试部"
    assert len(data["identities"]) == 1
    assert data["identities"][0]["source_system"] == "gitlab"
    assert len(data["teams"]) == 1
    assert data["teams"][0]["team_name"] == "虚拟组X"
    assert data["teams"][0]["allocation"] == 0.8

def test_api_create_team_and_add_member(db_session):
    """测试通过 API 创建团队并添加成员。"""
    # 1. 创建用户并赋予管理员角色
    u_id = uuid.uuid4()
    admin_user = User(global_user_id=u_id, full_name="系统管理员", primary_email="admin@ex.com", employee_id="ADMIN1", is_current=True)
    admin_role = Role(code="SYSTEM_ADMIN", name="管理员")
    db_session.add_all([admin_user, admin_role])
    db_session.commit()
    
    db_session.execute(user_roles.insert().values(user_id=u_id, role_id=admin_role.id))
    db_session.commit()

    # 由于 TestClient 与 db_session 共享物理库但不是同一个 Session，我们需要重新加载
    db_admin = db_session.query(User).filter_by(global_user_id=u_id).first()

    # 强行设置当前用户为 Admin (模拟 Depends(get_current_user))
    from devops_portal.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: db_admin

    # 2. 创建团队
    payload = {
        "name": "API 团队",
        "team_code": "API_TEAM",
        "description": "通过 API 创建"
    }
    resp = client.post("/admin/teams", json=payload)
    assert resp.status_code == 200
    team_id = resp.json()["id"]

    # 3. 添加成员
    member_payload = {
        "user_id": str(u_id),
        "role_code": "LEADER",
        "allocation_ratio": 1.0
    }
    resp = client.post(f"/admin/teams/{team_id}/members", json=member_payload)
    assert resp.status_code == 200

    # 4. 验证数据库
    # 物理库共享，直接查
    db_team = db_session.query(Team).filter_by(id=team_id).first()
    assert len(db_team.members) == 1
    assert db_team.members[0].role_code == "LEADER"

    # 清理覆盖
    app.dependency_overrides.pop(get_current_user)

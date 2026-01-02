import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models import Base
from devops_collector.models.base_models import ProjectMaster, Organization
from devops_collector.plugins.gitlab.models import Project

@pytest.fixture
def db_session():
    """创建内存数据库会话。"""
    engine = create_engine('sqlite:///:memory:')
    # Mock PostgreSQL specific types for SQLite
    import sqlalchemy
    from sqlalchemy.dialects import postgresql
    postgresql.UUID = lambda *args, **kwargs: sqlalchemy.String(36)
    
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_project_master_creation(db_session):
    """测试 ProjectMaster 模型的创建。"""
    org = Organization(org_id="DEPT_IT_001", org_name="IT部门", is_current=True)
    db_session.add(org)
    
    pm = ProjectMaster(
        project_id="PRJ_TEST_001",
        project_name="测试主项目",
        project_type="SPRINT",
        status="PLAN",
        org_id="DEPT_IT_001",
        budget_code="B_2026_01",
        budget_type="CAPEX"
    )
    db_session.add(pm)
    db_session.commit()
    
    retrieved = db_session.query(ProjectMaster).filter_by(project_id="PRJ_TEST_001").first()
    assert retrieved is not None
    assert retrieved.project_name == "测试主项目"
    assert retrieved.org_id == "DEPT_IT_001"

def test_project_linkage_and_lead_repo(db_session):
    """测试两层架构中的关联逻辑与受理仓库。"""
    # 1. 创建主项目
    pm = ProjectMaster(
        project_id="MDM_PAY_001",
        project_name="支付系统",
        org_id="DEPT_PAY"
    )
    db_session.add(pm)
    
    # 2. 创建技术仓库并关联
    repo1 = Project(id=101, name="Pay-Frontend", path_with_namespace="pay/frontend")
    repo2 = Project(id=102, name="Pay-Backend", path_with_namespace="pay/backend")
    
    repo1.mdm_project_id = pm.project_id
    repo2.mdm_project_id = pm.project_id
    
    # 设置 repo2 为受理中心
    pm.lead_repo_id = repo2.id
    
    db_session.add_all([repo1, repo2])
    db_session.commit()
    
    # 3. 验证
    retrieved_pm = db_session.query(ProjectMaster).first()
    assert len(retrieved_pm.gitlab_repos) == 2
    assert retrieved_pm.lead_repo_id == 102
    
    # 验证反向关系
    assert repo1.mdm_project.project_name == "支付系统"

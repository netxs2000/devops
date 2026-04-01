"""TODO: Add module description."""

import uuid
from unittest.mock import MagicMock, patch

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from devops_collector.auth.auth_database import get_auth_db as get_db
from devops_collector.models import (
    Base,
    Organization,
    Product,
    ProjectMaster,
    ProjectProductRelation,
    User,
)
from devops_collector.models import SysRole as Role
from devops_collector.plugins.gitlab.models import GitLabProject as Project
from devops_portal.dependencies import get_current_user
from devops_collector.auth import auth_service
from devops_collector.auth.auth_dependency import get_user_gitlab_client
from devops_portal.main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    '''"""TODO: Add description."""'''
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class MockUserContext:
    '''"""TODO: Add class description."""'''

    def __init__(self):
        self.user = None


mock_context = MockUserContext()


async def override_get_current_user():
    return mock_context.user


async def override_get_gitlab_client():
    return MagicMock()


@pytest.fixture
def client():
    """Create a TestClient with overridden dependencies for this module."""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[auth_service.get_current_user_obj] = override_get_current_user
    app.dependency_overrides[get_user_gitlab_client] = override_get_gitlab_client
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试用例前重置数据库。"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    org = db.query(Organization).filter_by(org_code="DEPT_TEST").first()
    if not org:
        org = Organization(org_code="DEPT_TEST", org_name="测试部门", is_current=True)
        db.add(org)
    admin_role = db.query(Role).filter_by(role_key="SYSTEM_ADMIN").first()
    if not admin_role:
        admin_role = Role(role_key="SYSTEM_ADMIN", role_name="系统管理员")
        db.add(admin_role)
    user_role = db.query(Role).filter_by(role_key="USER").first()
    if not user_role:
        user_role = Role(role_key="USER", role_name="普通用户")
        db.add(user_role)
    db.commit()
    db.query(User).delete()
    db.commit()
    admin_user = User(global_user_id=uuid.uuid4(), full_name="Admin User", primary_email="admin@example.com")
    admin_user.roles.append(admin_role)
    normal_user = User(
        global_user_id=uuid.uuid4(),
        full_name="Normal User",
        primary_email="user@example.com",
        department_id=org.id,
    )
    normal_user.roles.append(user_role)
    db.add_all([admin_user, normal_user])
    db.commit()
    db.close()
    yield
    # Disable foreign keys for cleanup to avoid IntegrityError with circular dependencies
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(bind=conn)
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")


def test_admin_create_project(client):
    """测试管理员创建 MDM 主项目。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == "admin@example.com").first()
    org = db.query(Organization).filter_by(org_code="DEPT_TEST").first()
    mock_context.user = admin

    payload = {
        "project_code": "PRJ_2026_NEW",
        "project_name": "New Integrated Project",
        "org_id": org.id,
        "project_type": "SPRINT",
        "status": "PLAN",
    }
    response = client.post("/admin/mdm-projects", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    pm = db.query(ProjectMaster).filter_by(project_code="PRJ_2026_NEW").first()
    assert pm is not None
    assert pm.project_name == "New Integrated Project"


def test_admin_link_and_set_lead_repo(client):
    """测试关联仓库并设置受理中心。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == "admin@example.com").first()
    mock_context.user = admin
    org = db.query(Organization).filter_by(org_code="DEPT_TEST").first()
    pm = ProjectMaster(project_code="PM_LINK_001", project_name="Link Project", org_id=org.id)
    repo = Project(id=999, name="Tech Repo", path_with_namespace="tech/repo")
    db.add_all([pm, repo])
    db.commit()
    payload = {"mdm_project_code": "PM_LINK_001", "gitlab_project_id": 999, "is_lead": True}
    response = client.post("/admin/link-repo", json=payload)
    assert response.status_code == 200
    db.refresh(pm)
    assert pm.lead_repo_id == 999
    db.refresh(repo)
    assert repo.mdm_project_id == pm.id


def test_service_desk_list_projects(client):
    """测试阶段 3.0: 基于产品维度的业务系统列表获取。"""
    db = TestingSessionLocal()
    org = db.query(Organization).filter_by(org_code="DEPT_TEST").first()

    # 1. 创建产品
    p1 = Product(product_code="PROD_ALPHA", product_name="Alpha System", is_current=True, product_description="Test", version_schema="SemVer")
    p2 = Product(product_code="PROD_BETA", product_name="Beta System", is_current=True, product_description="Hidden", version_schema="SemVer")
    db.add_all([p1, p2])
    db.flush()

    # 2. 创建关联项目并配置受理中心 (只有 p1 配置)
    pm1 = ProjectMaster(
        project_code="PM_ALPHA",
        project_name="Alpha Repo",
        org_id=org.id,
        lead_repo_id=101,
        is_current=True,
    )
    db.add(pm1)
    db.flush()

    rel1 = ProjectProductRelation(product_id=p1.id, project_id=pm1.id, org_id=org.id)
    db.add(rel1)
    db.commit()

    user = db.query(User).filter(User.primary_email == "user@example.com").first()
    mock_context.user = user

    response = client.get("/service-desk/business-projects")
    assert response.status_code == 200
    data = response.json()

    # 此处逻辑：p1 有受理仓即返回受限列表，若都没有则返回全量。
    # 当前 p1 有受理仓，应只回 p1
    assert any(item["id"] == "PROD_ALPHA" for item in data)
    # p2 没有关联有受理仓的项目，在 list_business_projects 的逻辑中，如果有产品有受理仓，则只回有的
    # 验证返回字段
    target = next(item for item in data if item["id"] == "PROD_ALPHA")
    assert target["name"] == "Alpha System"


@patch("devops_portal.routers.service_desk_router.ServiceDeskService")
def test_submit_bug_via_product_code(MockServiceDeskService, client):
    """测试基于产品 Business ID 提交 Bug 的三层映射逻辑。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == "admin@example.com").first()
    mock_context.user = admin
    org = db.query(Organization).filter_by(org_code="DEPT_TEST").first()

    # 设置三层映射：Product -> ProjectProductRelation -> ProjectMaster(lead_repo)
    p = Product(product_code="BIZ_SYSTEM_A", product_name="Business System A", is_current=True, product_description="A", version_schema="SemVer")
    db.add(p)
    db.flush()

    pm = ProjectMaster(
        project_code="PM_CORP_001",
        project_name="Corporate Project",
        org_id=org.id,
        lead_repo_id=555,
        is_current=True,
    )
    db.add(pm)
    db.flush()

    rel = ProjectProductRelation(product_id=p.id, project_id=pm.id, org_id=org.id)
    db.add(rel)
    db.commit()

    mock_service = MockServiceDeskService.return_value

    async def async_create_ticket(*args, **kwargs):
        return MagicMock(id=12345)

    mock_service.create_ticket.side_effect = async_create_ticket
    payload = {
        "title": "Integrated Test Bug",
        "severity": "Major",
        "environment": "SIT",
        "steps_to_repro": "Steps...",
        "actual_result": "Broken",
        "expected_result": "Fixed",
        "bug_category": "Functional",
        "attachments": [],
    }
    # 使用 product_code 调用 API
    response = client.post("/service-desk/submit-bug?mdm_id=BIZ_SYSTEM_A", json=payload)
    assert response.status_code == 200
    assert "BUG-12345" in response.json()["tracking_code"]
    mock_service.create_ticket.assert_called_once()
    args, kwargs = mock_service.create_ticket.call_args
    assert kwargs["project_id"] == 555
    assert "Corporate Project" in kwargs["title"]


def test_submit_bug_no_lead_repo(client):
    """测试未配置受理仓时的提交报错。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == "admin@example.com").first()
    mock_context.user = admin
    org = db.query(Organization).filter_by(org_code="DEPT_TEST").first()

    # 创建产品但关联的项目没有 lead_repo_id
    p = Product(product_code="PROD_NO_REPO", product_name="No Repo Product", is_current=True, product_description="N", version_schema="SemVer")
    db.add(p)
    db.flush()

    pm = ProjectMaster(project_code="PM_NO_REPO", project_name="No Repo Project", org_id=org.id, lead_repo_id=None, is_current=True)
    db.add(pm)
    db.flush()

    rel = ProjectProductRelation(product_id=p.id, project_id=pm.id, org_id=org.id)
    db.add(rel)
    db.commit()

    payload = {
        "title": "Bad Bug",
        "severity": "Major",
        "environment": "SIT",
        "steps_to_repro": "...",
        "actual_result": "Error",
        "expected_result": "No error",
        "attachments": [],
    }
    response = client.post("/service-desk/submit-bug?mdm_id=PROD_NO_REPO", json=payload)
    assert response.status_code == 400
    assert "未配置线上受理中心" in response.json()["detail"]

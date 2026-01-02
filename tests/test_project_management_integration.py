import pytest
import uuid
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from devops_portal.main import app
from devops_collector.models import Base, ProjectMaster, Organization, User, Project, Role
from devops_collector.auth.router import get_db
from devops_portal.dependencies import get_current_user
from unittest.mock import MagicMock, patch

# --- 数据库配置 ---
# 使用内存 SQLite 进行集成测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- 依赖项覆盖 ---
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# 全局变量用于控制模拟的用户
class MockUserContext:
    def __init__(self):
        self.user = None

mock_context = MockUserContext()

async def override_get_current_user():
    return mock_context.user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    """每个测试用例前重置数据库。"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # 初始化必要的基础数据
    org = db.query(Organization).filter_by(org_id="DEPT_TEST").first()
    if not org:
        org = Organization(org_id="DEPT_TEST", org_name="测试部门", is_current=True)
        db.add(org)
    
    # 创建或获取角色
    admin_role = db.query(Role).filter_by(code="SYSTEM_ADMIN").first()
    if not admin_role:
        admin_role = Role(code="SYSTEM_ADMIN", name="系统管理员")
        db.add(admin_role)
        
    user_role = db.query(Role).filter_by(code="USER").first()
    if not user_role:
        user_role = Role(code="USER", name="普通用户")
        db.add(user_role)
    
    db.commit()

    # 清理并创建测试用户
    db.query(User).delete()
    db.commit()

    admin_user = User(
        global_user_id=uuid.uuid4(),
        full_name="Admin User",
        primary_email="admin@example.com"
    )
    admin_user.roles.append(admin_role)

    normal_user = User(
        global_user_id=uuid.uuid4(),
        full_name="Normal User",
        primary_email="user@example.com",
        department_id="DEPT_TEST"
    )
    normal_user.roles.append(user_role)

    db.add_all([admin_user, normal_user])
    db.commit()
    db.close()
    
    yield
    # 保持连接池活跃的情况下，不 drop_all 也可以，但为了安全我们做 truncate
    # 或者在这里 drop
    Base.metadata.drop_all(bind=engine)

# --- 测试用例 ---

def test_admin_create_project():
    """测试管理员创建 MDM 主项目。"""
    # 设置当前用户为 Admin
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == "admin@example.com").first()
    mock_context.user = admin
    
    payload = {
        "project_id": "PRJ_2026_NEW",
        "project_name": "New Integrated Project",
        "org_id": "DEPT_TEST",
        "project_type": "SPRINT",
        "status": "PLAN"
    }
    
    response = client.post("/admin/mdm-projects", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # 验证数据库
    pm = db.query(ProjectMaster).filter_by(project_id="PRJ_2026_NEW").first()
    assert pm is not None
    assert pm.project_name == "New Integrated Project"

def test_admin_link_and_set_lead_repo():
    """测试关联仓库并设置受理中心。"""
    # 设置当前用户为 Admin
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == "admin@example.com").first()
    mock_context.user = admin
    
    # 1. 先创建一个主项目
    pm = ProjectMaster(project_id="PM_LINK_001", project_name="Link Project", org_id="DEPT_TEST")
    # 2. 创建一个技术仓库
    repo = Project(id=999, name="Tech Repo", path_with_namespace="tech/repo")
    db.add_all([pm, repo])
    db.commit()
    
    # 3. 调用关联 API 并设置为 Lead
    payload = {
        "mdm_project_id": "PM_LINK_001",
        "gitlab_project_id": 999,
        "is_lead": True
    }
    response = client.post("/admin/link-repo", json=payload)
    assert response.status_code == 200
    
    # 4. 验证主项目的 lead_repo_id 是否更新
    db.refresh(pm)
    assert pm.lead_repo_id == 999
    
    # 5. 验证仓库的 mdm_project_id 是否更新
    db.refresh(repo)
    assert repo.mdm_project_id == "PM_LINK_001"

def test_service_desk_list_projects():
    """测试业务侧获取可选项目列表（组织隔离）。"""
    db = TestingSessionLocal()
    # 创建一个属于 DEPT_TEST 的项目，并配置了受理仓库
    pm1 = ProjectMaster(project_id="PM_SD_001", project_name="Visible Project", org_id="DEPT_TEST", lead_repo_id=101, is_current=True)
    # 创建一个属于其他部门的项目
    pm2 = ProjectMaster(project_id="PM_SD_002", project_name="Hidden Project", org_id="DEPT_OTHER", lead_repo_id=102, is_current=True)
    db.add_all([pm1, pm2])
    db.commit()
    
    # 设置当前用户为 Normal User (所属 DEPT_TEST)
    # 设置当前用户为 Normal User (所属 DEPT_TEST)
    user = db.query(User).filter(User.primary_email == "user@example.com").first()
    mock_context.user = user
    
    # 模拟隐私过滤器 (这里需要注意 apply_plugin_privacy_filter 的实现)
    # 如果 apply_plugin_privacy_filter 涉及复杂的组织树，可能需要进一步 mock
    with patch('devops_portal.routers.service_desk.apply_plugin_privacy_filter') as mock_filter:
        # 直接让 mock 返回过滤后的查询
        mock_filter.side_effect = lambda db, query, model, user: query.filter(model.org_id == user.department_id)
        
        response = client.get("/service-desk/business-projects")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["id"] == "PM_SD_001"

@patch('devops_portal.routers.service_desk.ServiceDeskService')
def test_submit_bug_via_mdm_id(MockServiceDeskService):
    """测试通过 MDM ID 提交 Bug 时的路由逻辑。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == "admin@example.com").first()
    mock_context.user = admin
    
    # 创建带受理仓的项目
    pm = ProjectMaster(project_id="PM_RT_001", project_name="Router Project", org_id="DEPT_TEST", lead_repo_id=555, is_current=True)
    db.add(pm)
    db.commit()
    
    # Mock ServiceDeskService
    mock_service = MockServiceDeskService.return_value
    # 模拟异步方法，使用 AsyncMock 或者手动设置 side_effect 为异步函数
    async def async_create_ticket(*args, **kwargs):
        return MagicMock(id=12345)
    mock_service.create_ticket.side_effect = async_create_ticket
    
    payload = {
        "title": "Integrated Test Bug",
        "severity": "Major",
        "environment": "SIT",
        "steps_to_repro": "1. Login; 2. Click button",
        "actual_result": "Something broken",
        "expected_result": "Should work",
        "attachments": []
    }
    
    # 提交 Bug，传入 mdm_id=PM_RT_001
    response = client.post("/service-desk/submit-bug?mdm_id=PM_RT_001", json=payload)
    
    assert response.status_code == 200
    assert "BUG-12345" in response.json()["tracking_code"]
    
    # 验证 service.create_ticket 是否收到了正确的 gitlab project_id (555)
    mock_service.create_ticket.assert_called_once()
    args, kwargs = mock_service.create_ticket.call_args
    assert kwargs["project_id"] == 555
    assert "Router Project" in kwargs["title"]

def test_submit_bug_no_lead_repo():
    """测试未配置受理仓时的提交报错。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == "admin@example.com").first()
    mock_context.user = admin
    
    # 创建没有受理仓的项目
    pm = ProjectMaster(project_id="PM_NO_LEAD", project_name="No Lead Project", org_id="DEPT_TEST", lead_repo_id=None, is_current=True)
    db.add(pm)
    db.commit()
    
    payload = {
        "title": "Bad Bug",
        "severity": "Major",
        "environment": "SIT",
        "steps_to_repro": "1. Login; 2. Click button",
        "actual_result": "Error",
        "expected_result": "No error",
        "attachments": []
    }
    
    response = client.post("/service-desk/submit-bug?mdm_id=PM_NO_LEAD", json=payload)
    assert response.status_code == 400
    assert "未配置受理中心仓库" in response.json()["detail"]

"""TODO: Add module description."""
import pytest
import uuid
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from devops_portal.main import app
from devops_collector.models import Base, ProjectMaster, Organization, User, GitLabProject as Project, Role
from devops_collector.auth.auth_database import get_auth_db as get_db
from devops_portal.dependencies import get_current_user
from unittest.mock import MagicMock, patch
SQLALCHEMY_DATABASE_URL = 'sqlite:///:memory:'
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

class MockUserContext:
    '''"""TODO: Add class description."""'''

    def __init__(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.user = None
mock_context = MockUserContext()

async def override_get_current_user():
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    return mock_context.user
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    """每个测试用例前重置数据库。"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    org = db.query(Organization).filter_by(org_id='DEPT_TEST').first()
    if not org:
        org = Organization(org_id='DEPT_TEST', org_name='测试部门', is_current=True)
        db.add(org)
    admin_role = db.query(Role).filter_by(code='SYSTEM_ADMIN').first()
    if not admin_role:
        admin_role = Role(code='SYSTEM_ADMIN', name='系统管理员')
        db.add(admin_role)
    user_role = db.query(Role).filter_by(code='USER').first()
    if not user_role:
        user_role = Role(code='USER', name='普通用户')
        db.add(user_role)
    db.commit()
    db.query(User).delete()
    db.commit()
    admin_user = User(global_user_id=uuid.uuid4(), full_name='Admin User', primary_email='admin@example.com')
    admin_user.roles.append(admin_role)
    normal_user = User(global_user_id=uuid.uuid4(), full_name='Normal User', primary_email='user@example.com', department_id='DEPT_TEST')
    normal_user.roles.append(user_role)
    db.add_all([admin_user, normal_user])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def test_admin_create_project():
    """测试管理员创建 MDM 主项目。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == 'admin@example.com').first()
    mock_context.user = admin
    payload = {'project_id': 'PRJ_2026_NEW', 'project_name': 'New Integrated Project', 'org_id': 'DEPT_TEST', 'project_type': 'SPRINT', 'status': 'PLAN'}
    response = client.post('/admin/mdm-projects', json=payload)
    assert response.status_code == 200
    assert response.json()['status'] == 'success'
    pm = db.query(ProjectMaster).filter_by(project_id='PRJ_2026_NEW').first()
    assert pm is not None
    assert pm.project_name == 'New Integrated Project'

def test_admin_link_and_set_lead_repo():
    """测试关联仓库并设置受理中心。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == 'admin@example.com').first()
    mock_context.user = admin
    pm = ProjectMaster(project_id='PM_LINK_001', project_name='Link Project', org_id='DEPT_TEST')
    repo = Project(id=999, name='Tech Repo', path_with_namespace='tech/repo')
    db.add_all([pm, repo])
    db.commit()
    payload = {'mdm_project_id': 'PM_LINK_001', 'gitlab_project_id': 999, 'is_lead': True}
    response = client.post('/admin/link-repo', json=payload)
    assert response.status_code == 200
    db.refresh(pm)
    assert pm.lead_repo_id == 999
    db.refresh(repo)
    assert repo.mdm_project_id == 'PM_LINK_001'

def test_service_desk_list_projects():
    """测试业务侧获取可选项目列表（组织隔离）。"""
    db = TestingSessionLocal()
    pm1 = ProjectMaster(project_id='PM_SD_001', project_name='Visible Project', org_id='DEPT_TEST', lead_repo_id=101, is_current=True)
    pm2 = ProjectMaster(project_id='PM_SD_002', project_name='Hidden Project', org_id='DEPT_OTHER', lead_repo_id=102, is_current=True)
    db.add_all([pm1, pm2])
    db.commit()
    user = db.query(User).filter(User.primary_email == 'user@example.com').first()
    mock_context.user = user
    with patch('devops_portal.routers.service_desk_router.apply_plugin_privacy_filter') as mock_filter:
        mock_filter.side_effect = lambda db, query, model, user: query.filter(model.org_id == user.department_id)
        response = client.get('/service-desk/business-projects')
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['id'] == 'PM_SD_001'

@patch('devops_portal.routers.service_desk_router.ServiceDeskService')
def test_submit_bug_via_mdm_id(MockServiceDeskService):
    """测试通过 MDM ID 提交 Bug 时的路由逻辑。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == 'admin@example.com').first()
    mock_context.user = admin
    pm = ProjectMaster(project_id='PM_RT_001', project_name='Router Project', org_id='DEPT_TEST', lead_repo_id=555, is_current=True)
    db.add(pm)
    db.commit()
    mock_service = MockServiceDeskService.return_value

    async def async_create_ticket(*args, **kwargs):
        '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return MagicMock(id=12345)
    mock_service.create_ticket.side_effect = async_create_ticket
    payload = {'title': 'Integrated Test Bug', 'severity': 'Major', 'environment': 'SIT', 'steps_to_repro': '1. Login; 2. Click button', 'actual_result': 'Something broken', 'expected_result': 'Should work', 'attachments': []}
    response = client.post('/service-desk/submit-bug?mdm_id=PM_RT_001', json=payload)
    assert response.status_code == 200
    assert 'BUG-12345' in response.json()['tracking_code']
    mock_service.create_ticket.assert_called_once()
    args, kwargs = mock_service.create_ticket.call_args
    assert kwargs['project_id'] == 555
    assert 'Router Project' in kwargs['title']

def test_submit_bug_no_lead_repo():
    """测试未配置受理仓时的提交报错。"""
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.primary_email == 'admin@example.com').first()
    mock_context.user = admin
    pm = ProjectMaster(project_id='PM_NO_LEAD', project_name='No Lead Project', org_id='DEPT_TEST', lead_repo_id=None, is_current=True)
    db.add(pm)
    db.commit()
    payload = {'title': 'Bad Bug', 'severity': 'Major', 'environment': 'SIT', 'steps_to_repro': '1. Login; 2. Click button', 'actual_result': 'Error', 'expected_result': 'No error', 'attachments': []}
    response = client.post('/service-desk/submit-bug?mdm_id=PM_NO_LEAD', json=payload)
    assert response.status_code == 400
    assert '未配置受理中心仓库' in response.json()['detail']
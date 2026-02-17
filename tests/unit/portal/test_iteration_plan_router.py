import pytest
from unittest.mock import MagicMock, patch
from devops_collector.models.base_models import User
from devops_collector.plugins.gitlab.models import GitLabProject, GitLabMilestone
from devops_portal.main import app

@pytest.fixture(autouse=True)
def setup_admin(mock_user):
    from devops_collector.models.base_models import SysRole
    admin_role = SysRole(role_key="SYSTEM_ADMIN", role_name="Admin")
    mock_user.roles = [admin_role]

@pytest.fixture
def mock_iteration_service():
    from devops_portal.routers.iteration_plan_router import get_iteration_plan_service
    mock = MagicMock()
    app.dependency_overrides[get_iteration_plan_service] = lambda: mock
    yield mock
    del app.dependency_overrides[get_iteration_plan_service]

def test_list_iteration_projects(authenticated_client, db_session):
    project = GitLabProject(
        id=101,
        name="Test Project",
        path_with_namespace="group/test-project"
    )
    db_session.add(project)
    db_session.commit()
    
    response = authenticated_client.get("/iteration-plan/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["id"] == 101

def test_list_milestones(authenticated_client, db_session):
    project = GitLabProject(id=101, name="P1", path_with_namespace="g/p1")
    db_session.add(project)
    
    milestone = GitLabMilestone(
        id=202,
        project_id=101,
        title="v1.0.0",
        state="active"
    )
    db_session.add(milestone)
    db_session.commit()
    
    response = authenticated_client.get("/iteration-plan/projects/101/milestones")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 202

def test_view_backlog(authenticated_client, mock_iteration_service):
    mock_iteration_service.get_backlog_issues.return_value = [{"iid": 1, "title": "Backlog Issue"}]
    
    response = authenticated_client.get("/iteration-plan/projects/101/backlog")
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Backlog Issue"

def test_plan_issue(authenticated_client, mock_iteration_service):
    mock_iteration_service.move_issue_to_sprint.return_value = True
    
    payload = {"issue_iid": 1, "milestone_id": 202}
    response = authenticated_client.post("/iteration-plan/projects/101/plan", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_trigger_release(authenticated_client, mock_iteration_service):
    mock_iteration_service.execute_release.return_value = {"status": "released", "tag": "v1.0.0"}
    
    payload = {
        "version": "v1.0.0",
        "new_title": "v1.0.0-final",
        "ref_branch": "main"
    }
    response = authenticated_client.post("/iteration-plan/projects/101/release", json=payload)
    assert response.status_code == 200
    assert response.json()["tag"] == "v1.0.0"

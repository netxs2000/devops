import pytest
from unittest.mock import MagicMock
from devops_collector.plugins.gitlab.models import GitLabProject, GitLabMilestone
from devops_portal.routers.iteration_plan_router import get_iteration_plan_service

def test_list_projects(authenticated_client, db_session):
    project = GitLabProject(
        id=1,
        name="test-project",
        path_with_namespace="group/test-project",
        web_url="http://gitlab.com/group/test-project"
    )
    db_session.add(project)
    db_session.commit()

    response = authenticated_client.get("/iteration-plan/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test-project"

def test_list_milestones(authenticated_client, db_session):
    milestone = GitLabMilestone(
        id=1,
        project_id=1,
        title="v1.0",
        state="active",
        due_date="2025-01-01"
    )
    db_session.add(milestone)
    db_session.commit()

    response = authenticated_client.get("/iteration-plan/projects/1/milestones")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "v1.0"

def test_create_milestone(authenticated_client):
    # Mock the service
    mock_service = MagicMock()
    mock_service.create_sprint.return_value = {"id": 1, "title": "v2.0"}
    
    # Override dependency
    from devops_portal.main import app
    app.dependency_overrides[get_iteration_plan_service] = lambda: mock_service

    payload = {
        "title": "v2.0",
        "start_date": "2025-02-01",
        "due_date": "2025-02-28",
        "description": "Sprint 2"
    }
    
    try:
        response = authenticated_client.post("/iteration-plan/projects/1/milestones", json=payload)
        assert response.status_code == 200
        assert response.json()["title"] == "v2.0"
        mock_service.create_sprint.assert_called_once()
    finally:
        app.dependency_overrides = {}

def test_view_backlog(authenticated_client):
    mock_service = MagicMock()
    mock_service.get_backlog_issues.return_value = [{"id": 1, "title": "Issue 1"}]
    
    from devops_portal.main import app
    app.dependency_overrides[get_iteration_plan_service] = lambda: mock_service
    
    try:
        response = authenticated_client.get("/iteration-plan/projects/1/backlog")
        assert response.status_code == 200
        assert response.json()[0]["title"] == "Issue 1"
    finally:
        app.dependency_overrides = {}

def test_view_sprint(authenticated_client):
    mock_service = MagicMock()
    mock_service.get_sprint_backlog.return_value = [{"id": 2, "title": "Issue 2"}]
    
    from devops_portal.main import app
    app.dependency_overrides[get_iteration_plan_service] = lambda: mock_service
    
    try:
        response = authenticated_client.get("/iteration-plan/projects/1/sprint/v1.0")
        assert response.status_code == 200
        assert response.json()[0]["title"] == "Issue 2"
    finally:
         app.dependency_overrides = {}

def test_plan_issue(authenticated_client):
    mock_service = MagicMock()
    mock_service.move_issue_to_sprint.return_value = True
    
    from devops_portal.main import app
    app.dependency_overrides[get_iteration_plan_service] = lambda: mock_service
    
    payload = {"issue_iid": 1, "milestone_id": 10}
    try:
        response = authenticated_client.post("/iteration-plan/projects/1/plan", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    finally:
        app.dependency_overrides = {}

def test_remove_issue(authenticated_client):
    mock_service = MagicMock()
    mock_service.remove_issue_from_sprint.return_value = True
    
    from devops_portal.main import app
    app.dependency_overrides[get_iteration_plan_service] = lambda: mock_service
    
    payload = {"issue_iid": 1}
    try:
        response = authenticated_client.post("/iteration-plan/projects/1/remove", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    finally:
        app.dependency_overrides = {}

def test_trigger_release(authenticated_client):
    mock_service = MagicMock()
    mock_service.execute_release.return_value = {"status": "released", "tag": "v1.0"}
    
    from devops_portal.main import app
    app.dependency_overrides[get_iteration_plan_service] = lambda: mock_service
    
    payload = {
        "version": "v1.0",
        "new_title": "Release v1.0",
        "ref_branch": "main",
        "auto_rollover": True
    }
    
    try:
        response = authenticated_client.post("/iteration-plan/projects/1/release", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "released"
    finally:
        app.dependency_overrides = {}

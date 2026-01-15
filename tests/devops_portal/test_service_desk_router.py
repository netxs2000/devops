import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from devops_collector.models.base_models import ProjectMaster, User
from devops_portal.routers.service_desk_router import ServiceDeskService, TestingService
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.auth.auth_dependency import get_user_gitlab_client
from devops_portal.dependencies import get_current_user
from devops_portal.main import app

@pytest.fixture
def mock_servicedesk_service():
    with patch("devops_portal.routers.service_desk_router.ServiceDeskService") as mock:
        yield mock.return_value

@pytest.fixture
def mock_gitlab_client():
    mock = MagicMock(spec=GitLabClient)
    return mock

def test_list_business_projects(authenticated_client, db_session):
    project = ProjectMaster(
        project_id="MDM001",
        project_name="Biz Project 1",
        is_current=True,
        lead_repo_id=10
    )
    db_session.add(project)
    db_session.commit()
    
    response = authenticated_client.get("/service-desk/business-projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "MDM001"

@pytest.mark.asyncio
async def test_upload_service_desk_attachment(authenticated_client, db_session, mock_gitlab_client):
    # Override the dependency for this test
    app.dependency_overrides[get_user_gitlab_client] = lambda: mock_gitlab_client

    project = ProjectMaster(
        project_id="MDM001",
        project_name="Biz Project 1",
        lead_repo_id=10
    )
    db_session.add(project)
    db_session.commit()
    
    # Mocking client response for upload
    # Note: The client logic might differ, usually it returns the response json
    # In service_desk_router.py: uploaded_file = client._post(...).json()
    # So we need to mock _post().json()
    mock_response = MagicMock()
    mock_response.json.return_value = {"markdown": "url", "url": "url"}
    mock_gitlab_client._post.return_value = mock_response
    mock_gitlab_client.get_project.return_value = {"id": 10}

    # Simulate file upload
    files = {'file': ('test.png', b'content', 'image/png')}
    response = authenticated_client.post("/service-desk/upload?mdm_id=MDM001", files=files)
    
    assert response.status_code == 200
    assert "url" in response.json()

@pytest.mark.asyncio
async def test_submit_bug(authenticated_client, db_session, mock_gitlab_client):
    app.dependency_overrides[get_user_gitlab_client] = lambda: mock_gitlab_client
    
    project = ProjectMaster(
        project_id="MDM001",
        project_name="Biz Project 1",
        lead_repo_id=10
    )
    db_session.add(project)
    db_session.commit()
    
    # Mock create_issue for create_ticket
    mock_gitlab_client.create_issue.return_value = {'iid': 100}

    payload = {
        "title": "Test Bug",
        "actual_result": "It failed",
        "expected_result": "It works",
        "steps_to_repro": "Step 1",
        "severity": "S2",
        "priority": "P1",
        "environment": "UAT",
        "attachments": []
    }
    response = authenticated_client.post("/service-desk/submit-bug?mdm_id=MDM001", json=payload)
    assert response.status_code == 200
    assert "BUG-1" in response.json()["tracking_code"]

@pytest.mark.asyncio
async def test_submit_requirement(authenticated_client, db_session, mock_gitlab_client):
    app.dependency_overrides[get_user_gitlab_client] = lambda: mock_gitlab_client

    project = ProjectMaster(
        project_id="MDM001",
        project_name="Biz Project 1",
        lead_repo_id=10
    )
    db_session.add(project)
    db_session.commit()

    mock_gitlab_client.create_issue.return_value = {'iid': 200}

    payload = {
        "title": "Test Req",
        "description": "I want feature X",
        "priority": "P2",
        "attachments": []
    }
    response = authenticated_client.post("/service-desk/submit-requirement?mdm_id=MDM001", json=payload)
    assert response.status_code == 200
    assert "REQ-1" in response.json()["tracking_code"]

def test_list_service_desk_tickets(authenticated_client, db_session):
    # This might fail if get_user_tickets relies on service implementation which now uses DB
    # We need to manually add tickets to DB to test this
    from devops_collector.models.service_desk import ServiceDeskTicket
    # ... setup user ... authenticated_client has mock_user
    # mock_user UUID? The conftest fixture mock_user defines global_user_id
    # We should fetch the mock_user to get its ID, or rely on conftest creating it with a known valid ID.
    # conftest mock_user uses: global_user_id=uuid.uuid4()
    # It might be dynamic.
    
    # However, authenticated_client fixture sets the override to lambda: mock_user.
    # We can access that user instance.
    mock_user = app.dependency_overrides[get_current_user]()
    
    ticket = ServiceDeskTicket(
        gitlab_project_id=10,
        gitlab_issue_iid=1,
        title="Test Ticket",
        requester_id=mock_user.global_user_id,
        status="opened",
        issue_type="bug"
    )
    db_session.add(ticket)
    db_session.commit()
    
    response = authenticated_client.get("/service-desk/tickets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Test Ticket"

def test_track_service_desk_ticket(authenticated_client, db_session):
    from devops_collector.models.service_desk import ServiceDeskTicket
    ticket = ServiceDeskTicket(
        gitlab_project_id=10,
        gitlab_issue_iid=1,
        title="Track Me",
        status="opened"
    )
    db_session.add(ticket)
    db_session.commit()
    
    response = authenticated_client.get(f"/service-desk/track/{ticket.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Track Me"

@pytest.mark.asyncio
async def test_update_ticket_status(authenticated_client, db_session, mock_gitlab_client):
    # This endpoint likely calls update_ticket_status which uses client if present
    # We should override get_user_gitlab_client to provide mock, though operation might succeed without it if code handles None
    # But router logic: service = ServiceDeskService() -> NO client instance in router by default unless updated?
    # In my update plan, I am NOT injecting client to update_ticket_status yet (step 169 router code did NOT have it).
    # Wait, in step 412 I ONLY updated submit_bug and submit_req.
    # Let's check update_ticket_status in router again.
    # It uses: service = ServiceDeskService() -> no client.
    # So it won't sync to GitLab. But DB update should work.
    
    from devops_collector.models.service_desk import ServiceDeskTicket
    ticket = ServiceDeskTicket(
        gitlab_project_id=10,
        gitlab_issue_iid=1,
        title="Update Me",
        status="opened"
    )
    db_session.add(ticket)
    db_session.commit()
    
    response = authenticated_client.patch(f"/service-desk/tickets/{ticket.id}/status?new_status=closed")
    assert response.status_code == 200
    assert response.json()["new_status"] == "closed"
    
    db_session.refresh(ticket)
    assert ticket.status == "closed"

def test_get_my_tickets(authenticated_client, db_session):
    mock_user = app.dependency_overrides[get_current_user]()
    
    from devops_collector.models.service_desk import ServiceDeskTicket
    # Ticket for user
    t1 = ServiceDeskTicket(
        gitlab_project_id=10, 
        gitlab_issue_iid=1, 
        title="My Ticket", 
        requester_id=mock_user.global_user_id,
        requester_email=mock_user.primary_email
    )
    # Ticket for other
    import uuid
    t2 = ServiceDeskTicket(
        gitlab_project_id=10, 
        gitlab_issue_iid=2, 
        title="Other Ticket", 
        requester_id=uuid.uuid4(),
        requester_email="other@example.com"
    )
    db_session.add(t1)
    db_session.add(t2)
    db_session.commit()
    
    response = authenticated_client.get("/service-desk/my-tickets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "My Ticket"

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from devops_collector.models.base_models import ProjectMaster
from devops_portal.routers.service_desk_router import ServiceDeskService, TestingService, GitLabClient

@pytest.fixture
def mock_servicedesk_service():
    with patch("devops_portal.routers.service_desk_router.ServiceDeskService") as mock:
        yield mock.return_value

@pytest.fixture
def mock_gitlab_client():
    with patch("devops_portal.routers.service_desk_router.GitLabClient") as mock:
        yield mock.return_value

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
    project = ProjectMaster(
        project_id="MDM001",
        project_name="Biz Project 1",
        lead_repo_id=10
    )
    db_session.add(project)
    db_session.commit()
    
    mock_project_obj = MagicMock()
    mock_project_obj.upload.return_value = {"markdown": "url", "url": "url"}
    mock_gitlab_client.get_project.return_value = mock_project_obj
    
    # Simulate file upload
    files = {'file': ('test.png', b'content', 'image/png')}
    response = authenticated_client.post("/service-desk/upload?mdm_id=MDM001", files=files)
    assert response.status_code == 200
    assert "url" in response.json()

@pytest.mark.asyncio
async def test_submit_bug(authenticated_client, db_session, mock_servicedesk_service):
    project = ProjectMaster(
        project_id="MDM001",
        project_name="Biz Project 1",
        lead_repo_id=10
    )
    db_session.add(project)
    db_session.commit()
    
    mock_ticket = MagicMock()
    mock_ticket.id = 123
    mock_servicedesk_service.create_ticket = AsyncMock(return_value=mock_ticket)
    
    payload = {
        "title": "Bug Title",
        "severity": "critical",
        "environment": "production",
        "steps_to_repro": "1. Do this",
        "actual_result": "It failed",
        "expected_result": "It should work",
        "attachments": []
    }
    
    response = authenticated_client.post("/service-desk/submit-bug?mdm_id=MDM001", json=payload)
    if response.status_code != 200:
        print(f"FAILED: {response.status_code} - {response.text}")
    assert response.status_code == 200
    assert response.json()["tracking_code"] == "BUG-123"

@pytest.mark.asyncio
async def test_submit_requirement(authenticated_client, db_session, mock_servicedesk_service):
    project = ProjectMaster(
        project_id="MDM001",
        project_name="Biz Project 1",
        lead_repo_id=10
    )
    db_session.add(project)
    db_session.commit()
    
    mock_ticket = MagicMock()
    mock_ticket.id = 456
    mock_servicedesk_service.create_ticket = AsyncMock(return_value=mock_ticket)
    
    payload = {
        "title": "Req Title",
        "description": "I need this",
        "priority": "P2",
        "req_type": "feature",
        "attachments": []
    }
    
    response = authenticated_client.post("/service-desk/submit-requirement?mdm_id=MDM001", json=payload)
    assert response.status_code == 200
    assert response.json()["tracking_code"] == "REQ-456"

def test_list_service_desk_tickets(authenticated_client, mock_servicedesk_service, mock_user):
    mock_ticket = MagicMock()
    mock_ticket.id = 1
    mock_ticket.title = "Ticket 1"
    mock_ticket.status = "opened"
    mock_ticket.issue_type = "bug"
    mock_ticket.origin_dept_name = "Dept A"
    mock_ticket.target_dept_name = "Dept B"
    # ISO Format
    from datetime import datetime
    mock_ticket.created_at = datetime(2025, 1, 1)
    
    mock_servicedesk_service.get_user_tickets.return_value = [mock_ticket]
    
    response = authenticated_client.get("/service-desk/tickets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Ticket 1"

def test_track_service_desk_ticket(authenticated_client, mock_servicedesk_service):
    mock_ticket = {"id": 1, "title": "Ticket 1", "status": "opened"}
    mock_servicedesk_service.get_ticket_by_id.return_value = mock_ticket
    
    response = authenticated_client.get("/service-desk/track/1")
    assert response.status_code == 200
    assert response.json()["title"] == "Ticket 1"

@pytest.mark.asyncio
async def test_update_ticket_status(authenticated_client, mock_servicedesk_service):
    mock_servicedesk_service.update_ticket_status = AsyncMock(return_value=True)
    
    response = authenticated_client.patch("/service-desk/tickets/1/status?new_status=closed")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_get_my_tickets(authenticated_client, mock_servicedesk_service, mock_user):
    # Mock user email in fixture is test@example.com
    mock_ticket = MagicMock()
    mock_ticket.id = 1
    mock_ticket.requester_email = "test@example.com"
    mock_ticket.title = "My Ticket"
    mock_ticket.status = "opened"
    mock_ticket.issue_type = "bug"
    from datetime import datetime
    mock_ticket.created_at = datetime(2025, 1, 1)

    mock_servicedesk_service.get_user_tickets.return_value = [mock_ticket]

    response = authenticated_client.get("/service-desk/my-tickets")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "My Ticket"

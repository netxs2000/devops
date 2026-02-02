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

from devops_collector.models.base_models import ProjectMaster, User, Product, ProjectProductRelation

def test_list_business_projects(authenticated_client, db_session):
    # Setup full chain: Product -> Relation -> Project
    pid = generate_id("MDM")
    prod_id = generate_id("PROD")
    
    project = ProjectMaster(
        project_id=pid,
        project_name="Biz Project 1",
        is_current=True,
        lead_repo_id=10
    )
    product = Product(
        product_id=prod_id,

        product_name="Core Product",
        product_description="Desc",
        is_current=True,
        version_schema="SemVer"
    )
    relation = ProjectProductRelation(
        project_id=pid,
        product_id=prod_id,
        org_id="ORG001"
    )
    
    db_session.add(project)
    db_session.add(product)
    db_session.add(relation)
    db_session.commit()
    
    response = authenticated_client.get("/service-desk/business-projects")
    assert response.status_code == 200
    data = response.json()
    # Should return products
    # Note: DB might contain data from other tests if cleanup failed
    # We check if OUR product is there
    ids = [p["id"] for p in data]
    assert prod_id in ids

@pytest.mark.asyncio
async def test_upload_service_desk_attachment(authenticated_client, db_session, mock_gitlab_client):
    # Override the dependency for this test
    app.dependency_overrides[get_user_gitlab_client] = lambda: mock_gitlab_client

    pid = generate_id("MDM")
    project = ProjectMaster(
        project_id=pid,
        project_name="Biz Project 1",
        lead_repo_id=10
    )
    db_session.add(project)
    db_session.commit()
    
    # Mocking client response for upload
    mock_response = MagicMock()
    mock_response.json.return_value = {"markdown": "url", "url": "url"}
    mock_gitlab_client._post.return_value = mock_response
    mock_gitlab_client.get_project.return_value = {"id": 10}

    # Simulate file upload
    files = {'file': ('test.png', b'content', 'image/png')}
    response = authenticated_client.post(f"/service-desk/upload?mdm_id={pid}", files=files)
    
    assert response.status_code == 200
    assert "url" in response.json()

@pytest.mark.asyncio
async def test_submit_bug(authenticated_client, db_session, mock_gitlab_client):
    app.dependency_overrides[get_user_gitlab_client] = lambda: mock_gitlab_client
    
    # Setup data for Join query
    product_id = generate_id("PROD_BUG")
    pid = generate_id("MDM")
    
    project = ProjectMaster(
        project_id=pid,
        project_name="Biz Project 1",
        lead_repo_id=10,
        is_current=True
    )
    product = Product(
        product_id=product_id,

        product_name="Product Bug",
        product_description="Desc",
        is_current=True,
        version_schema="SemVer"
    )
    relation = ProjectProductRelation(
        project_id=pid,
        product_id=product_id,
        org_id="ORG001"
    )
    db_session.add(project)
    db_session.add(product)
    db_session.add(relation)
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
    # Pass product_id as mdm_id per router logic
    response = authenticated_client.post(f"/service-desk/submit-bug?mdm_id={product_id}", json=payload)
    if response.status_code != 200:
        print(response.json())
        
    assert response.status_code == 200
    assert "BUG" in response.json()["tracking_code"]

@pytest.mark.asyncio
async def test_submit_requirement(authenticated_client, db_session, mock_gitlab_client):
    app.dependency_overrides[get_user_gitlab_client] = lambda: mock_gitlab_client

    product_id = generate_id("PROD_REQ")
    pid = generate_id("MDM")
    
    project = ProjectMaster(
        project_id=pid,
        project_name="Biz Project 1",
        lead_repo_id=10,
        is_current=True
    )
    product = Product(
        product_id=product_id,

        product_name="Product Req",
        product_description="Desc",
        is_current=True,
        version_schema="SemVer"
    )
    relation = ProjectProductRelation(
        project_id=pid,
        product_id=product_id,
        org_id="ORG001"
    )
    db_session.add(project)
    db_session.add(product)
    db_session.add(relation)
    db_session.commit()

    mock_gitlab_client.create_issue.return_value = {'iid': 200}
    
    payload = {
        "title": "Test Req",
        "description": "I want feature X",
        "priority": "P2",
        "attachments": []
    }
    response = authenticated_client.post(f"/service-desk/submit-requirement?mdm_id={product_id}", json=payload)
    assert response.status_code == 200
    assert "REQ" in response.json()["tracking_code"]

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
    
    title = f"Test Ticket {uuid.uuid4()}"
    ticket = ServiceDeskTicket(
        gitlab_project_id=10,
        gitlab_issue_iid=1,
        title=title,
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
    # Check if ANY ticket matches ours
    titles = [t["title"] for t in data]
    assert title in titles

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

import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, User, Organization
from devops_collector.models.service_desk import ServiceDeskTicket
from devops_collector.plugins.gitlab.service_desk_service import ServiceDeskService
import uuid

@pytest.fixture
def session():
    """Create a memory SQLite database and session for integration testing."""
    engine = create_engine("sqlite:///:memory:")
    # Import all models to ensure metadata is populated
    from devops_collector.models import service_desk # ensure registered
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def mock_user(session):
    dept = Organization(org_id="DEPT001", org_name="IT Dept")
    session.add(dept)
    
    user = User(
        global_user_id=uuid.uuid4(),
        username="int_test_user",
        primary_email="int_test@example.com",
        full_name="Integration User",
        department_id="DEPT001"
    )
    session.add(user)
    session.commit()
    return user

@pytest.fixture
def mock_gitlab_client():
    mock = MagicMock()
    # Setup create_issue return
    mock.create_issue.return_value = {
        'iid': 888,
        'web_url': 'http://gitlab/issue/888'
    }
    return mock

@pytest.mark.asyncio
async def test_service_desk_full_flow(session, mock_user, mock_gitlab_client):
    """
    Integration Test for Service Desk:
    1. Initialize Service with Mock Client.
    2. Create a ticket -> Should save to DB and call Mock Client.
    3. Retrieve tickets -> Should find the created one.
    4. Update status -> Should update DB and call Mock Client.
    """
    # 1. Initialize Service
    service = ServiceDeskService(client=mock_gitlab_client)
    
    # 2. Create Ticket
    ticket = await service.create_ticket(
        db=session,
        project_id=100,
        title="Integration Test Ticket",
        description="Testing flow",
        issue_type="bug",
        requester=mock_user,
        attachments=["log.txt"]
    )
    
    assert ticket is not None
    assert ticket.id is not None
    assert ticket.gitlab_issue_iid == 888
    assert ticket.title == "Integration Test Ticket"
    assert ticket.origin_dept_name == "IT Dept" # From mock_user relation
    
    # Verify Client Call
    mock_gitlab_client.create_issue.assert_called_once()
    args, kwargs = mock_gitlab_client.create_issue.call_args
    assert args[0] == 100 # project_id
    assert args[1]['title'] == "Integration Test Ticket"
    assert "log.txt" in args[1]['description']
    
    # 3. Retrieve Tickets
    tickets = service.get_user_tickets(session, mock_user)
    assert len(tickets) == 1
    assert tickets[0].id == ticket.id
    
    # 4. Update Status (Close)
    success = await service.update_ticket_status(
        db=session,
        ticket_id=ticket.id,
        new_status="closed",
        operator_name="Admin"
    )
    
    assert success is True
    
    # Verify DB Update
    session.refresh(ticket)
    assert ticket.status == "closed"
    
    # Verify Client Call
    mock_gitlab_client.update_issue.assert_called_once()
    args, kwargs = mock_gitlab_client.update_issue.call_args
    assert args[0] == 100 # project_id
    assert args[1] == 888 # iid
    assert args[2] == {'state_event': 'close'}

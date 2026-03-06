from unittest.mock import AsyncMock, patch

import pytest

from devops_collector.auth import auth_service
from devops_portal.main import app
from devops_portal.routers.test_management_router import (
    get_test_management_service,
)
from devops_portal.schemas import TestCase


@pytest.fixture
def mock_test_service():
    with patch("devops_portal.routers.test_management_router.TestManagementService") as mock:
        service_instance = mock.return_value
        # Register dependency override
        app.dependency_overrides[get_test_management_service] = lambda: service_instance
        yield service_instance
        if get_test_management_service in app.dependency_overrides:
            del app.dependency_overrides[get_test_management_service]


def test_list_test_cases(authenticated_client, mock_test_service):
    # Setup mock return
    mock_case = TestCase(
        id=1,
        iid=101,
        title="Test Login",
        priority="P1",
        test_type="Functional",
        steps=[],
        result="parsed",
        web_url="http://gitlab/issue/101",
    )
    mock_test_service.get_test_cases = AsyncMock(return_value=[mock_case])

    response = authenticated_client.get("/test-management/projects/1/test-cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Login"


@pytest.mark.asyncio
async def test_create_test_case(authenticated_client, mock_test_service, mock_user):
    mock_test_service.create_test_case = AsyncMock(return_value={"iid": 102, "title": "New Case"})

    payload = {
        "title": "New Case",
        "priority": "P2",
        "test_type": "Functional",
        "steps": [{"action": "Click", "expected_result": "Done"}],
        "pre_conditions": "None",
    }

    response = authenticated_client.post("/test-management/projects/1/test-cases", json=payload)
    assert response.status_code == 200
    assert response.json()["issue"]["iid"] == 102


@pytest.mark.asyncio
async def test_execute_test_case(authenticated_client, mock_test_service, mock_user):
    mock_test_service.execute_test_case = AsyncMock(return_value=True)

    response = authenticated_client.post("/test-management/projects/1/test-cases/101/execute?result=passed")
    assert response.status_code == 200
    assert response.json()["new_result"] == "passed"


@pytest.mark.asyncio
async def test_get_test_summary(authenticated_client, mock_test_service):
    mock_case_passed = TestCase(id=1, iid=1, title="Pass", priority="P1", test_type="Func", steps=[], result="passed", web_url="http://gitlab/1")
    mock_case_failed = TestCase(id=2, iid=2, title="Fail", priority="P1", test_type="Func", steps=[], result="failed", web_url="http://gitlab/2")

    mock_test_service.get_test_cases = AsyncMock(return_value=[mock_case_passed, mock_case_failed])

    response = authenticated_client.get("/test-management/projects/1/test-summary")
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] == 1
    assert data["failed"] == 1
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_import_test_cases_forbidden(authenticated_client, mock_test_service, mock_user, monkeypatch):
    # Trigger 403 by mocking the token payload to have NO roles
    token_payload = {
        "sub": mock_user.primary_email,
        "roles": [],  # No roles
        "permissions": [],
    }
    monkeypatch.setattr(auth_service, "auth_decode_access_token", lambda t: token_payload if t == "mock-token" else None)

    files = {"file": ("test.csv", b"title,priority\nT1,P1", "text/csv")}
    response = authenticated_client.post("/test-management/projects/1/test-cases/import", files=files)
    assert response.status_code == 403

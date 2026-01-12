import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from devops_portal.schemas import TestCaseCreate, TestCase, TestStep
from devops_portal.routers.test_management_router import TestManagementService

@pytest.fixture
def mock_test_service():
    with patch("devops_portal.routers.test_management_router.TestManagementService") as mock:
        service_instance = mock.return_value
        yield service_instance

def test_list_test_cases(authenticated_client, mock_test_service):
    # Setup mock return
    mock_case = TestCase(
        id=1, iid=101, title="Test Login",
        priority="P1", test_type="Functional",
        steps=[], result='parsed',
        web_url="http://gitlab/issue/101"
    )
    mock_test_service.get_test_cases = AsyncMock(return_value=[mock_case])

    response = authenticated_client.get("/test-management/projects/1/test-cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Login"

@pytest.mark.asyncio
async def test_create_test_case(authenticated_client, mock_test_service, mock_user):
    # Mock check_permission dependency? 
    # check_permission returns a dependency function.
    # In test_management_router.py: current_user=Depends(check_permission(['maintainer', 'admin']))
    # We need to override this dependency or ensure mock_user satisfies it.
    # Since we are using authenticated_client which overrides get_current_user,
    # but check_permission USES get_current_user.
    # The check_permission function *returns* a callable that is used as dependency.
    # We should override the RESULT of that callable.
    
    # Actually, check_permission returns a function `permission_checker`.
    # FastAPI resolves `Depends(check_permission(...))` by calling `check_permission(...)` first to get the checker,
    # then calling that checker as a dependency.
    # So we can't easily override it by key unless we know the exact function object, which is created dynamically.
    
    # HOWEVER, checking `devops_portal/dependencies.py`:
    # check_permission returns `permission_checker`.
    # `permission_checker` takes `current_user`.
    # Inside, it checks `currrent_user.roles`.
    # So we just need to ensure `mock_user` has the right roles.
    
    from devops_collector.models.base_models import Role
    mock_user.roles.append(Role(code="maintainer"))
    
    mock_test_service.create_test_case = AsyncMock(return_value={"iid": 102, "title": "New Case"})
    
    payload = {
        "title": "New Case",
        "priority": "P2",
        "test_type": "Functional",
        "steps": [{"action": "Click", "expected_result": "Done"}],
        "pre_conditions": "None"
    }
    
    response = authenticated_client.post("/test-management/projects/1/test-cases", json=payload)
    if response.status_code != 200:
        print(response.json())
        
    assert response.status_code == 200
    assert response.json()["issue"]["iid"] == 102

@pytest.mark.asyncio
async def test_execute_test_case(authenticated_client, mock_test_service, mock_user):
    from devops_collector.models.base_models import Role
    # Check permission requires: tester, maintainer, or admin
    mock_user.roles.append(Role(code="tester"))
    
    mock_test_service.execute_test_case = AsyncMock(return_value=True)
    
    response = authenticated_client.post(
        "/test-management/projects/1/test-cases/101/execute?result=passed"
    )
    assert response.status_code == 200
    assert response.json()["new_result"] == "passed"

@pytest.mark.asyncio
async def test_get_test_summary(authenticated_client, mock_test_service):
    mock_case_passed = TestCase(
        id=1, iid=1, title="Pass", priority="P1", test_type="Func",
        steps=[], result='passed'
    )
    mock_case_failed = TestCase(
        id=2, iid=2, title="Fail", priority="P1", test_type="Func",
        steps=[], result='failed'
    )
    
    mock_test_service.get_test_cases = AsyncMock(return_value=[mock_case_passed, mock_case_failed])
    
    response = authenticated_client.get("/test-management/projects/1/test-summary")
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] == 1
    assert data["failed"] == 1
    assert data["total"] == 2

@pytest.mark.asyncio
async def test_import_test_cases_error(authenticated_client, mock_test_service, mock_user):
    # Missing role
    # mock_user roles are persistent across tests if we modify the fixture object?
    # No, fixture scope is function, but we are modifying the object returned by fixture.
    # Wait, the `mock_user` fixture in conftest is just an object creation.
    # BUT `authenticated_client` uses `app.dependency_overrides[get_current_user] = lambda: mock_user`.
    # So yes, if we modified `mock_user` in previous test, it might persist if not reset.
    # But `mock_user` fixture is scope="function" (default) or whatever in conftest.
    # Checking conftest: `@pytest.fixture` (default scope function).
    # So every test gets a new mock_user object.
    
    # Here we DO NOT add role. So it should fail 403.
    # Wait, check_permission logic: if 'SYSTEM_ADMIN' in roles -> pass.
    # If not, check if any of required in roles.
    # The default mock_user role attribute is "admin", but roles list is empty or depending on initialization in conftest.
    # In conftest:
    # return User(..., role="admin")
    # But User.roles is a relationship. It will be empty list [].
    # So check_permission(['maintainer', 'admin']) will fail if we check roles list.
    # The code `user_role_codes = [r.code for r in current_user.roles]`.
    # So we expect 403.
    
    files = {'file': ('test.csv', b'title,priority\nT1,P1', 'text/csv')}
    response = authenticated_client.post("/test-management/projects/1/test-cases/import", files=files)
    assert response.status_code == 403


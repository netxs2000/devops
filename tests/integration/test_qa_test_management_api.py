"""测试管理模块集成测试。

验证 REST API 路由与 TestManagementService 的协同工作。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from devops_collector.auth import auth_service
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.auth.auth_dependency import get_user_gitlab_client
from devops_collector.core import security
from devops_portal import schemas
from devops_portal.dependencies import get_current_user
from devops_portal.main import app


# Mock 依赖函数
mock_db = MagicMock()
mock_user = MagicMock(full_name="Tester Zhang", role="admin")
mock_user.global_user_id = 1
mock_gitlab_client = MagicMock()

# Mock Token Payload
mock_token_payload = {
    "sub": "test@example.com",
    "roles": ["admin", security.ADMIN_ROLE_KEY],
    "permissions": [security.ADMIN_PERMISSION_WILDCARD],
}


def override_get_db():
    yield mock_db


async def override_get_current_user():
    return mock_user


async def override_get_user_gitlab_client():
    return mock_gitlab_client


@pytest.fixture
def client():
    """Create a TestClient with overridden dependencies for this module."""
    app.dependency_overrides[get_auth_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_user_gitlab_client] = override_get_user_gitlab_client

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_auth(monkeypatch):
    monkeypatch.setattr(auth_service, "auth_decode_access_token", lambda t: mock_token_payload if t == "mock-token" else None)
    monkeypatch.setattr(auth_service, "auth_get_current_user", lambda db, t: mock_user if t == "mock-token" else None)


@pytest.fixture
def mock_service():
    with patch("devops_portal.routers.test_management_router.TestManagementService", autospec=True) as MockService:
        service_instance = MockService.return_value
        yield service_instance


def test_list_test_cases_api_should_return_data(client, mock_service):
    # 打桩：模拟 Service 返回数据
    mock_service.get_test_cases = AsyncMock(
        return_value=[
            schemas.TestCase(
                global_issue_id=1,
                gitlab_issue_iid=101,
                title="Test API Case",
                priority="P1",
                issue_type="Functional",
                result="pending",
                web_url="http://gitlab.com/101",
            )
        ]
    )

    headers = {"Authorization": "Bearer mock-token"}
    response = client.get("/test-management/projects/1/test-cases", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["iid"] == 101
    assert data[0]["title"] == "Test API Case"


def test_execute_test_case_api_should_success(client, mock_service):
    # 打桩：模拟执行成功
    mock_service.execute_test_case = AsyncMock(return_value=True)

    headers = {"Authorization": "Bearer mock-token"}
    response = client.post("/test-management/projects/1/test-cases/101/execute?result=passed", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["new_result"] == "passed"

    # 验证是否正确传递了参数
    mock_service.execute_test_case.assert_called_once()
    args = mock_service.execute_test_case.call_args[0]
    assert args[1] == 101  # issue_iid
    assert args[2] == "passed"  # result


def test_get_test_summary_api_should_summarize(client, mock_service):
    # 打桩：模拟 Service 返回用例列表，Router 内部会进行统计
    mock_service.get_test_cases = AsyncMock(
        return_value=[
            schemas.TestCase(global_issue_id=1, gitlab_issue_iid=101, title="C1", result="passed"),
            schemas.TestCase(global_issue_id=2, gitlab_issue_iid=102, title="C2", result="failed"),
        ]
    )

    headers = {"Authorization": "Bearer mock-token"}
    response = client.get("/test-management/projects/1/test-summary", headers=headers)

    assert response.status_code == 200
    summary = response.json()
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["total"] == 2

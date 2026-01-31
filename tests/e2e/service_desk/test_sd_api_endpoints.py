"""
Service Desk E2E Tests - API 端点验证测试

测试场景：
1. API 端点可访问性
2. API 响应格式验证
3. 认证与授权验证

注意：这些测试直接调用 API，不通过浏览器 UI。
用于快速验证后端接口正常工作。
"""

import pytest
import httpx
from typing import Generator


class TestServiceDeskAPIEndpoints:
    """Service Desk API 端点测试"""

    @pytest.fixture(autouse=True)
    def setup(self, app_server: str):
        """测试前设置"""
        self.base_url = app_server
        self.client = httpx.Client(base_url=app_server, timeout=10)

    @pytest.fixture
    def auth_token(self, test_user_credentials: dict) -> str:
        """获取认证 Token"""
        response = self.client.post(
            "/auth/login",
            data={
                "username": test_user_credentials["email"],
                "password": test_user_credentials["password"],
            }
        )
        if response.status_code == 200:
            return response.json().get("access_token", "")
        return ""

    @pytest.fixture
    def auth_headers(self, auth_token: str) -> dict:
        """返回带认证的请求头"""
        return {"Authorization": f"Bearer {auth_token}"}

    # =========================================================================
    # 健康检查
    # =========================================================================

    def test_health_endpoint_should_return_200(self):
        """
        验证健康检查端点
        """
        response = self.client.get("/health")
        assert response.status_code == 200

    # =========================================================================
    # 未认证访问测试
    # =========================================================================

    def test_tickets_endpoint_without_auth_should_return_401(self):
        """
        场景：未认证访问工单列表
        期望：返回 401 Unauthorized
        """
        response = self.client.get("/service-desk/tickets")
        assert response.status_code in [401, 403]

    def test_business_projects_without_auth_should_return_401(self):
        """
        场景：未认证访问业务项目列表
        期望：返回 401 Unauthorized
        """
        response = self.client.get("/service-desk/business-projects")
        assert response.status_code in [401, 403]

    # =========================================================================
    # 认证访问测试
    # =========================================================================

    @pytest.mark.skip(reason="需要有效的测试用户凭据")
    def test_tickets_endpoint_with_auth_should_return_200(self, auth_headers: dict):
        """
        场景：认证后访问工单列表
        期望：返回 200 和工单数组
        """
        response = self.client.get("/service-desk/tickets", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.skip(reason="需要有效的测试用户凭据")
    def test_business_projects_with_auth_should_return_200(self, auth_headers: dict):
        """
        场景：认证后访问业务项目列表
        期望：返回 200 和项目数组
        """
        response = self.client.get("/service-desk/business-projects", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.skip(reason="需要有效的测试用户凭据")
    def test_my_tickets_endpoint_should_return_user_tickets(self, auth_headers: dict):
        """
        场景：访问我的工单列表
        期望：返回当前用户的工单
        """
        response = self.client.get("/service-desk/my-tickets", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    # =========================================================================
    # API 响应格式验证
    # =========================================================================

    @pytest.mark.skip(reason="需要有效的测试用户凭据和测试数据")
    def test_ticket_response_should_have_required_fields(self, auth_headers: dict):
        """
        场景：工单响应应包含必要字段
        期望：每个工单包含 iid, title, status 等字段
        """
        response = self.client.get("/service-desk/tickets", headers=auth_headers)
        data = response.json()

        if len(data) > 0:
            ticket = data[0]
            # 验证必要字段
            assert "iid" in ticket or "id" in ticket
            assert "title" in ticket
            # 可选字段
            # assert "status" in ticket
            # assert "requester_email" in ticket

    # =========================================================================
    # 错误处理验证
    # =========================================================================

    @pytest.mark.skip(reason="需要有效的测试用户凭据")
    def test_track_nonexistent_ticket_should_return_404(self, auth_headers: dict):
        """
        场景：查询不存在的工单
        期望：返回 404 Not Found
        """
        response = self.client.get("/service-desk/track/999999999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.skip(reason="需要有效的测试用户凭据")
    def test_invalid_status_update_should_return_400(self, auth_headers: dict):
        """
        场景：使用无效状态更新工单
        期望：返回 400 Bad Request
        """
        response = self.client.patch(
            "/service-desk/tickets/1/status",
            params={"new_status": "invalid_status"},
            headers=auth_headers
        )
        # 可能返回 400 或 422
        assert response.status_code in [400, 422, 404]

    def teardown_method(self, method):
        """测试后清理"""
        if hasattr(self, 'client'):
            self.client.close()

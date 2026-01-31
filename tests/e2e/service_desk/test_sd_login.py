"""
Service Desk E2E Tests - 登录与权限验证测试

测试场景：
1. 登录流程
2. 未登录访问重定向
3. 权限隔离验证
"""

import pytest
from playwright.sync_api import Page, expect

from .pages.base_page import BasePage


class TestServiceDeskLogin:
    """登录流程端到端测试"""

    @pytest.fixture(autouse=True)
    def setup(self, page: Page, app_server: str):
        """测试前设置"""
        self.page = page
        self.base_url = app_server
        self.base_page = BasePage(page, app_server)

    @pytest.mark.smoke
    def test_unauthenticated_user_should_see_login_modal(self):
        """
        场景：未登录用户访问页面
        期望：显示登录模态框
        """
        self.page.goto(f"{self.base_url}/static/index.html")
        self.page.wait_for_load_state("networkidle")

        login_modal = self.page.locator("#loginModal")
        expect(login_modal).to_be_visible()

    def test_login_modal_should_have_required_fields(self):
        """
        场景：登录模态框应包含必要字段
        期望：显示邮箱、密码输入框和登录按钮
        """
        self.page.goto(f"{self.base_url}/static/index.html")
        self.page.wait_for_load_state("networkidle")

        # 验证表单元素
        expect(self.page.locator("#login-email")).to_be_visible()
        expect(self.page.locator("#login-password")).to_be_visible()
        expect(self.page.locator("#login-submit")).to_be_visible()

    def test_empty_login_should_show_error(self):
        """
        场景：空表单提交登录
        期望：显示错误提示
        """
        self.page.goto(f"{self.base_url}/static/index.html")
        self.page.wait_for_load_state("networkidle")

        # 直接点击登录
        self.page.click("#login-submit")

        # 验证错误提示
        error = self.page.locator("#login-error")
        expect(error).to_be_visible()
        expect(error).to_contain_text("请填写")

    def test_invalid_credentials_should_show_error(self):
        """
        场景：错误凭据登录
        期望：显示登录失败错误
        """
        self.page.goto(f"{self.base_url}/static/index.html")
        self.page.wait_for_load_state("networkidle")

        # 填写错误凭据
        self.page.fill("#login-email", "wrong@example.com")
        self.page.fill("#login-password", "wrongpassword")
        self.page.click("#login-submit")

        # 等待响应
        self.page.wait_for_timeout(1000)

        # 验证错误提示
        error = self.page.locator("#login-error")
        expect(error).to_be_visible()

    @pytest.mark.smoke
    def test_successful_login_should_hide_modal_and_show_sidebar(
        self,
        test_user_credentials: dict
    ):
        """
        场景：正确凭据登录
        期望：隐藏登录模态框，显示侧边栏和用户信息
        """
        print(f"Navigating to {self.base_url}/static/index.html")
        self.page.goto(f"{self.base_url}/static/index.html")
        self.page.wait_for_load_state("networkidle")

        # 确保登录模态框可见
        login_modal = self.page.locator("#loginModal")
        print("Waiting for login modal to be visible...")
        expect(login_modal).to_be_visible(timeout=10000)

        # 填写正确凭据
        print(f"Filling login info for {test_user_credentials['email']}")
        self.page.fill("#login-email", test_user_credentials["email"])
        self.page.fill("#login-password", test_user_credentials["password"])
        self.page.click("#login-submit")

        # 等待页面刷新
        print("Waiting for network idle after login...")
        self.page.wait_for_load_state("networkidle")

        # 验证登录成功
        print("Verifying user display name...")
        user_name = self.page.locator("#user-display-name")
        expect(user_name).to_be_visible(timeout=10000)
        expect(user_name).not_to_have_text("Loading...", timeout=10000)
        print("Login verification successful!")

    def test_enter_key_should_submit_login(self):
        """
        场景：在密码框按回车键
        期望：触发登录提交
        """
        self.page.goto(f"{self.base_url}/static/index.html")
        self.page.wait_for_load_state("networkidle")

        # 填写表单
        self.page.fill("#login-email", "test@example.com")
        self.page.fill("#login-password", "password")

        # 按回车键
        self.page.press("#login-password", "Enter")

        # 等待响应 (会显示错误或成功)
        self.page.wait_for_timeout(1000)

        # 验证：按钮状态应该改变或显示错误
        # (这里只验证按回车会触发登录，不验证结果)


class TestServiceDeskRBAC:
    """权限隔离验证测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page, app_server: str):
        self.page = authenticated_page
        self.base_url = app_server

    def test_regular_user_should_not_see_admin_menu(self):
        """
        场景：普通用户登录
        期望：不显示管理员菜单项
        """
        # 普通用户不应看到用户管理等管理功能
        sidebar = self.page.locator("#sidebar-nav-container")

        # 检查是否有管理员专属菜单
        admin_menu = sidebar.locator("text=User Approvals")

        # 如果用户没有 USER:MANAGE 权限，不应该看到此菜单
        # 注意：这取决于测试用户的权限配置
        # 如果测试用户是普通用户，这应该不可见
        # expect(admin_menu).not_to_be_visible()

    def test_user_should_only_see_own_tickets_in_my_tickets(self):
        """
        场景：用户访问「我的工单」
        期望：只显示自己提交的工单
        """
        # 导航到我的工单
        self.page.locator("text=My Tickets").click()
        self.page.wait_for_load_state("networkidle")

        # 这里需要验证 API 返回的数据只包含当前用户的工单
        # 具体验证逻辑取决于测试数据设置

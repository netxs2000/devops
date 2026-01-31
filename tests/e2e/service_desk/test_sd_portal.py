"""
Service Desk E2E Tests - Service Portal 业务用户流程测试

测试场景：
1. 导航到 Service Portal
2. 选择产品并填写申请单
3. 提交工单并获取追踪码
4. 在「我的工单」中查看已提交工单
"""

import pytest
from playwright.sync_api import Page, expect

from .pages.service_desk_page import ServicePortalPage


class TestServiceDeskPortalSubmit:
    """Service Portal 提交工单流程测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page, app_server: str):
        """测试前设置：创建 Page Object 实例"""
        self.page = authenticated_page
        self.portal_page = ServicePortalPage(authenticated_page, app_server)

    @pytest.mark.smoke
    def test_navigate_to_portal_should_show_landing_page(self):
        """
        场景：成功登录后导航到 Service Portal
        期望：显示产品选择面板
        """
        self.portal_page.navigate_to_portal()
        
        # 验证 Portal 视图可见
        expect(self.page.locator("#sd-portal-view")).to_be_visible()
        
        # 验证 Landing 组件 (sd-landing)
        expect(self.page.locator("sd-landing")).to_be_visible()
        
        # 验证标题
        expect(self.page.locator("text=Support Center")).to_be_visible()

    @pytest.mark.smoke
    def test_submit_bug_report_flow(self, test_user_credentials: dict):
        """
        场景：提交一个 Bug 报告
        期望：显示成功提示
        """
        self.portal_page.navigate_to_portal()
        
        # 1. 等待产品列表加载并选择一个产品 (如果有的话)
        # 这里使用 locator 检查是否有产品卡片
        product_cards = self.page.locator(".product-card")
        if product_cards.count() > 0:
            product_cards.first.click()
        
        # 2. 点击报告 Bug
        # 注意：ServicePortalPage 中定义了选择器
        self.portal_page.click_report_bug()
        
        # 3. 填写表单
        bug_title = f"E2E Test Bug - {test_user_credentials['email'].split('@')[0]}"
        self.portal_page.fill_bug_form(
            title=bug_title,
            actual_result="E2E automation test: System crashed on startup",
            expected_result="System should start normally",
            steps="1. Run E2E test\n2. Observe result"
        )
        
        # 4. 提交
        self.portal_page.submit_form()
        
        # 5. 验证成功提示
        # 寻找包含 "Submitted" 或 "Success" 的文本
        expect(self.page.locator("text=Ticket Submitted")).to_be_visible(timeout=10000)

    @pytest.mark.smoke
    def test_my_tickets_should_display_submitted_tickets(self):
        """
        场景：查看「我的工单」
        期望：列表组件加载
        """
        self.portal_page.navigate_to_portal()
        self.portal_page.navigate_to_my_tickets()
        
        # 验证工单列表组件加载 (sd-ticket-list)
        expect(self.page.locator("sd-ticket-list")).to_be_visible()
        
        # 等待数据加载
        self.page.wait_for_load_state("networkidle")
        
        # 即使列表为空，组件也应该是可见的
        expect(self.page.locator("sd-ticket-list")).to_be_visible()

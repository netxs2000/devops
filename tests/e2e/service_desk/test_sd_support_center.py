"""
Service Desk E2E Tests - Support Center 工单管理测试

测试场景：
1. 工单列表加载与显示
2. 工单转缺陷流程
3. 工单转需求流程
4. 工单驳回流程
5. AI RCA 助手调用
"""

import pytest
from playwright.sync_api import Page, expect

from .pages.service_desk_page import ServiceDeskPage


class TestServiceDeskSupportCenter:
    """Service Desk Support Center (RD 视图) 端到端测试"""

    # =========================================================================
    # Fixtures
    # =========================================================================

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page, app_server: str):
        """测试前设置：创建 Page Object 实例"""
        self.page = authenticated_page
        self.sd_page = ServiceDeskPage(authenticated_page, app_server)

    # =========================================================================
    # 工单列表测试
    # =========================================================================

    @pytest.mark.smoke
    def test_navigate_to_support_center_should_show_ticket_list(self):
        """
        场景：导航到 Support Center
        期望：显示工单列表视图
        """
        self.sd_page.navigate_to_support_center()

        # 验证 Support View 可见
        support_view = self.page.locator("#sd-support-view")
        expect(support_view).to_be_visible()

        # 验证标题
        title = self.page.locator("text=Support Center")
        expect(title).to_be_visible()

    @pytest.mark.smoke
    def test_ticket_list_should_load_tickets_from_api(self):
        """
        场景：工单列表应从 API 加载数据
        期望：列表显示工单或空状态
        """
        self.sd_page.navigate_to_support_center()
        self.sd_page.wait_for_tickets_loaded()

        ticket_list = self.sd_page.get_ticket_list()
        expect(ticket_list).to_be_visible()

        # 列表要么有工单，要么显示空状态
        ticket_count = self.sd_page.get_ticket_count()
        if ticket_count == 0:
            self.sd_page.assert_empty_state()
        else:
            self.sd_page.assert_has_tickets()

    def test_sync_button_should_refresh_ticket_list(self):
        """
        场景：点击同步按钮
        期望：刷新工单列表
        """
        self.sd_page.navigate_to_support_center()
        self.sd_page.wait_for_tickets_loaded()

        # 记录当前状态
        initial_count = self.sd_page.get_ticket_count()

        # 点击同步
        self.sd_page.click_sync_button()

        # 验证列表刷新 (至少没有报错)
        self.sd_page.wait_for_tickets_loaded()

    # =========================================================================
    # 工单操作测试 (需要测试数据)
    # =========================================================================

    @pytest.mark.skip(reason="需要预置测试工单数据")
    def test_convert_ticket_to_defect_should_open_bug_form(self, seed_pending_ticket: dict):
        """
        场景：点击「转入缺陷」按钮
        期望：打开缺陷表单，预填工单信息
        """
        ticket_iid = seed_pending_ticket["iid"]
        ticket_title = seed_pending_ticket["title"]

        self.sd_page.navigate_to_support_center()
        self.sd_page.wait_for_tickets_loaded()

        # 验证工单存在
        self.sd_page.assert_ticket_exists(ticket_iid)

        # 点击转入缺陷
        self.sd_page.convert_to_defect(ticket_iid)

        # 验证 Bug 表单打开
        bug_modal = self.page.locator("#bugModalOverlay")
        expect(bug_modal).to_be_visible()

        # 验证标题预填
        bug_title = self.page.locator("#quick-bug-title")
        expect(bug_title).to_have_value(f"[Bug Transferred] {ticket_title}")

    @pytest.mark.skip(reason="需要预置测试工单数据")
    def test_convert_ticket_to_requirement_should_open_req_form(self, seed_pending_ticket: dict):
        """
        场景：点击「转入需求」按钮
        期望：打开需求表单，预填工单信息
        """
        ticket_iid = seed_pending_ticket["iid"]
        ticket_title = seed_pending_ticket["title"]

        self.sd_page.navigate_to_support_center()
        self.sd_page.wait_for_tickets_loaded()

        self.sd_page.convert_to_requirement(ticket_iid)

        # 验证需求表单打开
        req_modal = self.page.locator("#reqModalOverlay")
        expect(req_modal).to_be_visible()

        # 验证标题预填
        req_title = self.page.locator("#req_title")
        expect(req_title).to_have_value(f"[Req Transferred] {ticket_title}")

    @pytest.mark.skip(reason="需要预置测试工单数据")
    def test_reject_ticket_should_close_and_remove_from_list(self, seed_pending_ticket: dict):
        """
        场景：驳回工单
        期望：工单从列表中移除，显示成功提示
        """
        ticket_iid = seed_pending_ticket["iid"]

        self.sd_page.navigate_to_support_center()
        self.sd_page.wait_for_tickets_loaded()

        # 驳回工单
        self.sd_page.reject_ticket(ticket_iid, "Works as Intended")

        # 验证成功提示
        toast = self.page.locator("#toast-container")
        expect(toast).to_contain_text("dismissed")

        # 验证工单从列表移除
        self.sd_page.wait_for_tickets_loaded()
        self.sd_page.assert_ticket_not_exists(ticket_iid)

    @pytest.mark.skip(reason="需要预置测试工单数据和 AI 服务")
    def test_ai_rca_should_open_analysis_modal(self, seed_pending_ticket: dict):
        """
        场景：点击 AI RCA 按钮
        期望：打开 RCA 分析模态框
        """
        ticket_iid = seed_pending_ticket["iid"]

        self.sd_page.navigate_to_support_center()
        self.sd_page.wait_for_tickets_loaded()

        self.sd_page.open_ai_rca(ticket_iid)

        # 验证 RCA 模态框打开
        rca_modal = self.page.locator("#rcaModalOverlay")
        expect(rca_modal).to_be_visible()


class TestServiceDeskTicketDisplay:
    """工单显示相关测试"""

    @pytest.fixture(autouse=True)
    def setup(self, authenticated_page: Page, app_server: str):
        self.page = authenticated_page
        self.sd_page = ServiceDeskPage(authenticated_page, app_server)

    def test_ticket_row_should_display_correct_info(self):
        """
        场景：工单行应正确显示信息
        期望：显示 IID、标题、提交人、创建时间
        """
        self.sd_page.navigate_to_support_center()
        self.sd_page.wait_for_tickets_loaded()

        if self.sd_page.get_ticket_count() == 0:
            pytest.skip("No tickets available for testing")

        # 获取第一个工单行
        first_row = self.sd_page.get_ticket_rows().first

        # 验证必要元素存在
        iid_el = first_row.locator(".js-ticket-iid")
        title_el = first_row.locator(".js-ticket-title")
        meta_el = first_row.locator(".js-ticket-meta")

        expect(iid_el).to_be_visible()
        expect(title_el).to_be_visible()
        expect(meta_el).to_be_visible()

        # 验证 IID 格式 (#123)
        iid_text = iid_el.inner_text()
        assert iid_text.startswith("#"), f"IID should start with #, got: {iid_text}"

    def test_ticket_action_buttons_should_be_visible(self):
        """
        场景：工单行应显示操作按钮
        期望：显示转缺陷、转需求、驳回、AI RCA 按钮
        """
        self.sd_page.navigate_to_support_center()
        self.sd_page.wait_for_tickets_loaded()

        if self.sd_page.get_ticket_count() == 0:
            pytest.skip("No tickets available for testing")

        first_row = self.sd_page.get_ticket_rows().first

        # 验证所有操作按钮存在
        expect(first_row.locator(".js-action-defect")).to_be_visible()
        expect(first_row.locator(".js-action-req")).to_be_visible()
        expect(first_row.locator(".js-action-reject")).to_be_visible()
        expect(first_row.locator(".js-action-ai-rca")).to_be_visible()

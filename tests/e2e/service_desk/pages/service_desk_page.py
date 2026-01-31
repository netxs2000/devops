"""
Service Desk Page Object

封装 Service Desk 模块的页面操作，包括：
- 工单列表操作
- 工单处理操作 (转缺陷、转需求、驳回)
- Support Center 视图
"""

from playwright.sync_api import Page, Locator, expect
from .base_page import BasePage


class ServiceDeskPage(BasePage):
    """Service Desk 页面对象"""

    # =========================================================================
    # 选择器常量
    # =========================================================================

    # 视图容器
    SUPPORT_VIEW = "#sd-support-view"
    PORTAL_VIEW = "#sd-portal-view"
    TICKET_LIST = "#servicedesk-list"

    # 工单行
    TICKET_ROW = ".js-ticket-row"
    TICKET_IID = ".js-ticket-iid"
    TICKET_TITLE = ".js-ticket-title"
    TICKET_META = ".js-ticket-meta"

    # 操作按钮
    BTN_DEFECT = ".js-action-defect"
    BTN_REQ = ".js-action-req"
    BTN_REJECT = ".js-action-reject"
    BTN_AI_RCA = ".js-action-ai-rca"
    BTN_SYNC = ".js-btn-sync-tickets"

    # =========================================================================
    # 导航方法
    # =========================================================================

    def navigate_to_support_center(self) -> None:
        """导航到 Support Center (RD 工单处理视图)"""
        self.goto_static()
        self.expand_sidebar_group("Service Desk")
        self.click_sidebar_link("Support Center")
        self.page.wait_for_selector(self.SUPPORT_VIEW, state="visible")

    def navigate_to_service_portal(self) -> None:
        """导航到 Service Portal (业务用户提交工单视图)"""
        self.goto_static()
        self.expand_sidebar_group("Service Desk")
        self.click_sidebar_link("Service Portal")
        self.page.wait_for_selector(self.PORTAL_VIEW, state="visible")

    # =========================================================================
    # 工单列表操作
    # =========================================================================

    def get_ticket_list(self) -> Locator:
        """获取工单列表容器"""
        return self.page.locator(self.TICKET_LIST)

    def get_ticket_rows(self) -> Locator:
        """获取所有工单行"""
        return self.page.locator(self.TICKET_ROW)

    def get_ticket_count(self) -> int:
        """获取工单数量"""
        return self.get_ticket_rows().count()

    def get_ticket_by_iid(self, iid: int) -> Locator:
        """根据 IID 获取工单行"""
        return self.page.locator(f"{self.TICKET_ROW}[data-iid='{iid}']")

    def get_ticket_by_title(self, title: str) -> Locator:
        """根据标题获取工单行"""
        return self.page.locator(f"{self.TICKET_ROW}:has-text('{title}')")

    def is_ticket_visible(self, iid: int) -> bool:
        """检查工单是否可见"""
        return self.get_ticket_by_iid(iid).is_visible()

    def wait_for_tickets_loaded(self, timeout: int = 10000) -> None:
        """等待工单列表加载完成"""
        ticket_list = self.get_ticket_list()
        # 等待加载提示消失
        loading_text = ticket_list.locator("text=Synchronizing")
        if loading_text.is_visible():
            loading_text.wait_for(state="hidden", timeout=timeout)

    def click_sync_button(self) -> None:
        """点击同步按钮刷新工单列表"""
        self.page.locator(self.BTN_SYNC).click()
        self.wait_for_tickets_loaded()

    # =========================================================================
    # 工单处理操作
    # =========================================================================

    def convert_to_defect(self, iid: int) -> None:
        """将工单转为缺陷"""
        row = self.get_ticket_by_iid(iid)
        row.locator(self.BTN_DEFECT).click()

    def convert_to_requirement(self, iid: int) -> None:
        """将工单转为需求"""
        row = self.get_ticket_by_iid(iid)
        row.locator(self.BTN_REQ).click()

    def reject_ticket(self, iid: int, reason: str = "Works as Intended") -> None:
        """
        驳回工单

        Args:
            iid: 工单 IID
            reason: 驳回原因
        """
        row = self.get_ticket_by_iid(iid)

        # 设置 dialog 处理器
        self.page.on("dialog", lambda dialog: dialog.accept(reason))

        row.locator(self.BTN_REJECT).click()

        # 等待 Toast 提示
        self.wait_for_toast("dismissed")

    def open_ai_rca(self, iid: int) -> None:
        """打开 AI RCA 助手"""
        row = self.get_ticket_by_iid(iid)
        row.locator(self.BTN_AI_RCA).click()

    # =========================================================================
    # 断言方法
    # =========================================================================

    def assert_ticket_exists(self, iid: int) -> None:
        """断言工单存在"""
        expect(self.get_ticket_by_iid(iid)).to_be_visible()

    def assert_ticket_not_exists(self, iid: int) -> None:
        """断言工单不存在 (已被处理)"""
        expect(self.get_ticket_by_iid(iid)).not_to_be_visible()

    def assert_ticket_title(self, iid: int, expected_title: str) -> None:
        """断言工单标题"""
        row = self.get_ticket_by_iid(iid)
        title = row.locator(self.TICKET_TITLE)
        expect(title).to_have_text(expected_title)

    def assert_empty_state(self) -> None:
        """断言工单列表为空"""
        empty_msg = self.get_ticket_list().locator("text=No pending business feedback")
        expect(empty_msg).to_be_visible()

    def assert_has_tickets(self) -> None:
        """断言工单列表不为空"""
        expect(self.get_ticket_rows().first).to_be_visible()


class ServicePortalPage(BasePage):
    """Service Portal 页面对象 (业务用户视图)"""

    # =========================================================================
    # 选择器常量
    # =========================================================================

    PORTAL_VIEW = "#sd-portal-view"

    # Web Components
    SD_LANDING = "sd-landing"
    SD_REQUEST_FORM = "sd-request-form"
    SD_TICKET_LIST = "sd-ticket-list"

    # =========================================================================
    # 导航方法
    # =========================================================================

    def navigate_to_portal(self) -> None:
        """导航到 Service Portal"""
        self.goto_static()
        self.expand_sidebar_group("Service Desk")
        self.click_sidebar_link("Service Portal")
        self.page.wait_for_selector(self.PORTAL_VIEW, state="visible")

    # =========================================================================
    # 表单操作
    # =========================================================================

    def select_product(self, product_id: str) -> None:
        """选择产品 (业务系统)"""
        # 这取决于 sd-landing 组件的具体实现
        selector = self.page.locator(f"{self.SD_LANDING} select, {self.SD_LANDING} .product-card")
        if selector.first.is_visible():
            # 如果是 select 元素
            self.page.select_option(f"{self.SD_LANDING} select", product_id)

    def click_report_bug(self) -> None:
        """点击报告 Bug 按钮"""
        self.page.locator(f"{self.SD_LANDING} button:has-text('Bug')").click()

    def click_submit_requirement(self) -> None:
        """点击提交需求按钮"""
        self.page.locator(f"{self.SD_LANDING} button:has-text('Requirement')").click()

    def fill_bug_form(
        self,
        title: str,
        actual_result: str = "",
        expected_result: str = "",
        steps: str = "",
        severity: str = "S2",
        priority: str = "P1",
    ) -> None:
        """
        填写 Bug 提交表单

        注意：具体字段 ID 取决于 sd-request-form 组件的实现
        """
        form = self.page.locator(self.SD_REQUEST_FORM)

        # 填写表单字段
        form.locator("input[name='title'], #sd-bug-title").fill(title)
        if actual_result:
            form.locator("textarea[name='actual_result'], #sd-bug-actual").fill(actual_result)
        if expected_result:
            form.locator("textarea[name='expected_result'], #sd-bug-expected").fill(expected_result)
        if steps:
            form.locator("textarea[name='steps'], #sd-bug-steps").fill(steps)

        # 选择下拉框
        severity_select = form.locator("select[name='severity']")
        if severity_select.is_visible():
            severity_select.select_option(severity)

        priority_select = form.locator("select[name='priority']")
        if priority_select.is_visible():
            priority_select.select_option(priority)

    def submit_form(self) -> None:
        """提交表单"""
        self.page.locator(f"{self.SD_REQUEST_FORM} button[type='submit'], "
                          f"{self.SD_REQUEST_FORM} button:has-text('Submit')").click()

    def get_tracking_code(self) -> str:
        """获取提交成功后的追踪码"""
        success_msg = self.page.locator(".sd-success-message, .tracking-code")
        success_msg.wait_for(state="visible")
        return success_msg.inner_text()

    # =========================================================================
    # 我的工单操作
    # =========================================================================

    def navigate_to_my_tickets(self) -> None:
        """导航到我的工单页面"""
        self.click_sidebar_link("My Tickets")

    def get_my_ticket_list(self) -> Locator:
        """获取我的工单列表"""
        return self.page.locator(self.SD_TICKET_LIST)

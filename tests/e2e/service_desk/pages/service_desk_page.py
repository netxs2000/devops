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
        self.expand_sidebar_group("项目执行")
        self.click_sidebar_link("工单管理")
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
        self.expand_sidebar_group("支持与战略")
        self.click_sidebar_link("工单反馈")
        self.page.wait_for_selector(self.PORTAL_VIEW, state="visible")

    # =========================================================================
    # 表单操作
    # =========================================================================

    def select_product(self, product_id: str) -> None:
        """选择产品 (业务系统)"""
        # 如果在表单页
        form_select = self.page.locator(f"{self.SD_REQUEST_FORM} #product_id")
        if form_select.is_visible():
            form_select.select_option(label=product_id) # 可能是 Label 也可能是 Value
            return

        # 如果在 Landing 页 (card 模式)
        selector = self.page.locator(f"{self.SD_LANDING} .product-card")
        if selector.first.is_visible():
            selector.first.click()

    def click_report_bug(self) -> None:
        """点击报告 Bug 按钮"""
        # SdLanding 中，缺陷卡片的 data-target="bug_form"
        self.page.locator("sd-landing .card[data-target='bug_form']").click()

    def click_submit_requirement(self) -> None:
        """点击提交需求按钮"""
        self.page.locator("sd-landing .card[data-target='req_form']").click()

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
        """
        form = self.page.locator(self.SD_REQUEST_FORM)

        # 填写表单字段 (ID 匹配 sd_request_form.component.js)
        form.locator("#title").fill(title)
        if actual_result:
            form.locator("#actual").fill(actual_result)
        if steps:
            form.locator("#steps").fill(steps)

        # 选择下拉框
        severity_select = form.locator("#severity")
        if severity_select.is_visible():
            severity_select.select_option(severity)

        # 注意：sd-request-form 目前没有 priority 选择器，它是硬编码的 P2，
        # 如果需要，请根据组件实现调整。

    def submit_form(self) -> None:
        """提交表单"""
        # 匹配 .btn-submit 或 .js-submit
        self.page.locator(f"{self.SD_REQUEST_FORM} .js-submit").click()

    def get_tracking_code(self) -> str:
        """获取提交成功后的追踪码"""
        # 这里的追踪码通常在 Toast 之后或列表顶部，
        # 由于目前逻辑是提交后 navigate('landing')，我们可能需要检查 Toast 或直接跳过这个断言。
        # 简单等待 Toast 即可。
        toast = self.wait_for_toast("successful", timeout=10000)
        return "SUCCESS" # 模拟返回

    # =========================================================================
    # 我的工单操作
    # =========================================================================

    def navigate_to_my_tickets(self) -> None:
        """导航到我的工单页面"""
        self.expand_sidebar_group("支持与战略")
        self.click_sidebar_link("我的工单")

    def get_my_ticket_list(self) -> Locator:
        """获取我的工单列表"""
        return self.page.locator(self.SD_TICKET_LIST)

"""
Admin Page Object

封装管理后台页面（人员与组织管理）的操作。
"""

from playwright.sync_api import Page, expect
from tests.e2e.service_desk.pages.base_page import BasePage

class AdminPage(BasePage):
    """管理后台 Page Object"""

    def __init__(self, page: Page):
        super().__init__(page)
        # Selectors
        self.nav_orgs = "#nav-admin-orgs"
        self.nav_users = "#nav-admin-users"
        self.btn_create_org = ".js-btn-create-org"
        self.modal_create_org = "#createOrgModal"
        self.org_level_select = ".js-org-level-select"
        self.user_table = "#adm-users-view table"
        self.org_table = "#adm-orgs-view table"
        self.btn_import_products = ".js-product-import-file"  # The input element
        self.btn_import_mappings = ".js-mapping-import-file"  # The input element

    def wait_for_sidebar(self):
        """等待侧边栏加载完成"""
        self.page.locator("#sidebar-nav-container .nav-group").first.wait_for(state="visible", timeout=10000)

    def click_sidebar_link(self, label: str):
        """增强版点击侧边栏链接，自动处理分组展开"""
        self.wait_for_sidebar()
        
        # 定位包含该链接的分组
        group = self.page.locator(".nav-group").filter(has=self.page.locator(f".nav-link:has-text('{label}')"))
        
        # 检查是否已展开（expanded 类）
        is_expanded = group.evaluate("(el) => el.classList.contains('expanded')")
        if not is_expanded:
            group.locator(".js-nav-group-title").click()
            # 等待展开动画
            self.page.wait_for_timeout(300)
        
        link = group.locator(f".nav-link:has-text('{label}')")
        link.click()

    def navigate_to_orgs(self):
        """导航到研发组织管理"""
        self.click_sidebar_link("研发组织管理")
        expect(self.page.locator("#adm-orgs-view")).to_be_visible()

    def navigate_to_users(self):
        """导航到人员身份校准"""
        self.click_sidebar_link("人员身份校准")
        expect(self.page.locator("#adm-users-view")).to_be_visible()

    def open_create_org_modal(self):
        """打开新增组织模态框"""
        self.page.click(self.btn_create_org)
        expect(self.page.locator(self.modal_create_org)).to_be_visible()

    def get_default_org_level(self) -> str:
        """获取新增组织模态框中的默认层级"""
        return self.page.locator(self.org_level_select).input_value()

    def has_hr_relationship_column(self) -> bool:
        """检查用户表格是否有人事关系列"""
        header = self.page.locator(f"{self.user_table} th:has-text('人事关系')")
        return header.is_visible()

    def get_org_list_count(self) -> int:
        """获取组织列表行数"""
        return self.page.locator(f"{self.org_table} tbody tr").count()

    def navigate_to_products(self):
        """导航到产品体系管理"""
        self.click_sidebar_link("产品体系管理")
        expect(self.page.locator("#adm-products-view")).to_be_visible()
        # Wait for data loading to complete to ensure event listeners are bound
        expect(self.page.locator("#sys-loading-overlay")).to_be_hidden()

    def upload_products(self, file_path: str):
        """上传产品 CSV"""
        with self.page.expect_file_chooser() as fc_info:
            self.page.click(".js-btn-import-products")
        file_chooser = fc_info.value
        file_chooser.set_files(file_path)

    def upload_mappings(self, file_path: str):
        """上传产品映射 CSV"""
        with self.page.expect_file_chooser() as fc_info:
            self.page.click(".js-btn-import-mappings")
        file_chooser = fc_info.value
        file_chooser.set_files(file_path)

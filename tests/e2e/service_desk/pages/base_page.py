"""
Base Page Object

提供所有 Page Object 的基类，封装常用的页面操作方法。
"""

from playwright.sync_api import Page, Locator, expect


class BasePage:
    """Page Object 基类"""

    def __init__(self, page: Page, base_url: str = "http://127.0.0.1:8000"):
        self.page = page
        self.base_url = base_url

    # =========================================================================
    # 导航方法
    # =========================================================================

    def goto(self, path: str = "") -> None:
        """导航到指定路径"""
        url = f"{self.base_url}{path}"
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")

    def goto_static(self) -> None:
        """导航到主静态页面"""
        self.goto("/static/index.html")

    # =========================================================================
    # 侧边栏导航
    # =========================================================================

    def click_sidebar_link(self, link_text: str) -> None:
        """点击侧边栏菜单链接"""
        sidebar = self.page.locator("#sidebar-nav-container")
        link = sidebar.locator(f".nav-link:has-text('{link_text}')")
        link.click()
        self.page.wait_for_load_state("networkidle")

    def expand_sidebar_group(self, group_text: str) -> None:
        """展开侧边栏分组"""
        group = self.page.locator(f".nav-group-title:has-text('{group_text}')")
        if group.is_visible():
            group.click()

    # =========================================================================
    # 等待方法
    # =========================================================================

    def wait_for_toast(self, message: str = None, timeout: int = 5000) -> Locator:
        """等待 Toast 提示出现"""
        toast = self.page.locator("#toast-container .toast")
        toast.wait_for(state="visible", timeout=timeout)
        if message:
            expect(toast).to_contain_text(message)
        return toast

    def wait_for_loading_complete(self, timeout: int = 10000) -> None:
        """等待加载状态完成"""
        loading = self.page.locator("#loading")
        if loading.is_visible():
            loading.wait_for(state="hidden", timeout=timeout)

    # =========================================================================
    # 模态框操作
    # =========================================================================

    def is_modal_visible(self, modal_id: str) -> bool:
        """检查模态框是否可见"""
        modal = self.page.locator(f"#{modal_id}")
        return modal.is_visible() and "u-hide" not in (modal.get_attribute("class") or "")

    def close_modal(self, modal_id: str) -> None:
        """关闭模态框"""
        modal = self.page.locator(f"#{modal_id}")
        close_btn = modal.locator("button:has-text('Cancel'), button:has-text('Close')")
        if close_btn.is_visible():
            close_btn.click()

    # =========================================================================
    # 用户信息
    # =========================================================================

    def get_current_user_name(self) -> str:
        """获取当前登录用户名"""
        return self.page.locator("#user-display-name").inner_text()

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        user_name = self.page.locator("#user-display-name")
        return user_name.is_visible() and user_name.inner_text() != "Loading..."

    # =========================================================================
    # 截图与调试
    # =========================================================================

    def take_screenshot(self, name: str = "screenshot") -> str:
        """截取当前页面截图"""
        path = f"test-results/{name}.png"
        self.page.screenshot(path=path, full_page=True)
        return path

    def print_console_errors(self) -> None:
        """打印控制台错误 (用于调试)"""
        # 需要在页面加载前设置监听器
        pass

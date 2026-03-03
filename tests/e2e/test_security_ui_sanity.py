import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
def test_security_ui_navigation_and_modal(page):
    """验证安全中心导航、列表展示及上传弹窗。"""
    # 1. 登录
    page.goto("/static/index.html")
    # 假设已经自动登录或处于登录状态，如果是本地环境

    # 2. 点击安全中心
    page.click("text=安全中心")

    # 3. 验证视图切换
    expect(page.locator("#sec-vulnerable-count")).to_be_visible()
    expect(page.locator("text=依赖安全扫描")).to_be_visible()

    # 4. 点击上传报告按钮
    page.click("button:has-text('上传报告')")

    # 5. 验证弹窗弹出
    expect(page.locator("#uploadModal")).to_be_visible()
    expect(page.locator("text=上传扫描报告")).to_be_visible()

    # 6. 验证选择项目下拉框是否存在
    expect(page.locator("#uploadProjectSelect")).to_be_visible()

    # 7. 关闭弹窗
    page.click("#uploadModal .btn-close")
    expect(page.locator("#uploadModal")).not_to_be_visible()

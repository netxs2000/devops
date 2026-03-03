import pytest
from playwright.sync_api import expect

from tests.e2e.admin.pages.admin_page import AdminPage


@pytest.mark.smoke
def test_okr_governance_view_loading(admin_page: AdminPage):
    """验证 OKR 治理中心视图加载及基本元素展示"""
    admin_page.goto_static()
    admin_page.navigate_to_okrs()

    # 标题验证
    expect(admin_page.page.locator("#adm-okrs-view .adm-title")).to_contain_text("OKR 治理中心")

    # 筛选器验证
    expect(admin_page.page.locator(".js-okr-period-select")).to_be_visible()
    expect(admin_page.page.locator(".js-okr-status-select")).to_be_visible()

    # 导出按钮验证
    expect(admin_page.page.locator(".js-btn-export-okrs")).to_be_visible()

    # 预览表格验证 (表头)
    expect(admin_page.page.locator("#adm-okrs-view th:has-text('目标标题')")).to_be_visible()
    expect(admin_page.page.locator("#adm-okrs-view th:has-text('目标进度')")).to_be_visible()


def test_okr_export_button_link(admin_page: AdminPage):
    """验证 OKR 导出按钮是否触发下载请求 (检查 URL 构造)"""
    admin_page.goto_static()
    admin_page.navigate_to_okrs()

    # 设置筛选器
    admin_page.page.select_option(".js-okr-period-select", "2024-Q1")
    admin_page.page.select_option(".js-okr-status-select", "ACTIVE")

    # 我们监听下载事件
    with admin_page.page.expect_download() as download_info:
        admin_page.page.click(".js-btn-export-okrs")

    download = download_info.value
    # 验证下载的 URL 包含正确的参数
    assert "/admin/export/okrs" in download.url
    assert "period=2024-Q1" in download.url
    assert "status=ACTIVE" in download.url

    # 验证建议的文件名
    assert "okr_export.csv" in download.suggested_filename

    # 可以在这里保存下载的文件供后续内容校验
    # download.save_as("test-results/okr_export.csv")


def test_okr_preview_empty_state(admin_page: AdminPage):
    """验证无数据时的预览表格状态"""
    admin_page.goto_static()
    admin_page.navigate_to_okrs()

    # 设置一个肯定没数据的筛选条件
    admin_page.page.select_option(".js-okr-period-select", "2025-Q2")

    # 等待加载遮罩消失（如果有的话）
    expect(admin_page.page.locator("#sys-loading-overlay")).to_be_hidden()

    # 验证空状态提示
    expect(admin_page.page.locator(".js-okr-preview-tbody")).to_contain_text("未找到符合条件的 OKR 数据")

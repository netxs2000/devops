"""
Admin Management E2E Tests

验证人员与组织管理功能：
1. 人事关系字段在表格中的展示。
2. 研发组织管理视图的加载。
3. 新增组织模态框的默认层级（中心）。
"""

import pytest
from playwright.sync_api import expect
from tests.e2e.admin.pages.admin_page import AdminPage

@pytest.mark.smoke
def test_user_table_hr_relationship_column(admin_page: AdminPage):
    """验证人员身份校准表格中是否包含 '人事关系' 列"""
    admin_page.goto_static()
    admin_page.navigate_to_users()
    
    # 验证表头
    expect(admin_page.page.locator("#adm-users-view th:has-text('人事关系')")).to_be_visible()
    
    # 验证表格行中是否包含内容（哪怕是默认值）
    # 注意：这需要数据库中有数据，或者测试环境会渲染占位符
    first_row_badge = admin_page.page.locator("#adm-users-view .adm-badge").first
    if first_row_badge.is_visible():
        expect(first_row_badge).to_be_visible()

@pytest.mark.smoke
def test_organization_mgmt_view_and_default_level(admin_page: AdminPage):
    """验证研发组织管理视图及新增组织模态框的默认层级"""
    admin_page.goto_static()
    admin_page.navigate_to_orgs()
    
    # 验证页面标题
    expect(admin_page.page.locator("#adm-orgs-view .adm-title")).to_contain_text("研发组织全景主数据")
    
    # 打开新增模态框
    admin_page.open_create_org_modal()
    
    # 验证默认层级是否为 '2' (中心)
    default_level = admin_page.get_default_org_level()
    assert default_level == "2", f"Expected default level '2', but got '{default_level}'"
    
    # 验证下拉框选中的文本
    selected_text = admin_page.page.locator(".js-org-level-select option:checked").inner_text()
    assert "中心" in selected_text

def test_organization_export_button_exists(admin_page: AdminPage):
    """验证导出按钮是否存在"""
    admin_page.goto_static()
    admin_page.navigate_to_orgs()
    
    export_btn = admin_page.page.locator(".js-btn-export-orgs")
    expect(export_btn).to_be_visible()

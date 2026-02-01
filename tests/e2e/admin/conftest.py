"""
Admin E2E Tests - Shared Fixtures
"""

import pytest
from playwright.sync_api import Page
from tests.e2e.admin.pages.admin_page import AdminPage

@pytest.fixture
def admin_page(authenticated_page: Page) -> AdminPage:
    """提供已登录管理员身份的 AdminPage 对象"""
    return AdminPage(authenticated_page)

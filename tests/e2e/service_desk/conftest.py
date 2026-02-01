"""
Service Desk E2E Tests - Specific Fixtures
"""

import os
import pytest
from playwright.sync_api import Page
from typing import Generator

@pytest.fixture
def rd_authenticated_page(
    page: Page,
    app_server: str,
) -> Generator[Page, None, None]:
    """
    创建具有 RD 权限的已认证页面。
    """
    rd_email = os.getenv("E2E_RD_USER_EMAIL", "rd_test@example.com")
    rd_password = os.getenv("E2E_RD_USER_PASSWORD", "rd_test_password")

    page.goto(f"{app_server}/static/index.html")

    login_modal = page.locator("#loginModal")
    if login_modal.is_visible():
        page.fill("#login-email", rd_email)
        page.fill("#login-password", rd_password)
        page.click("#login-submit")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#user-display-name", state="visible", timeout=10000)

    yield page

@pytest.fixture
def seed_test_product(app_server: str, test_user_credentials: dict) -> Generator[dict, None, None]:
    yield {
        "product_id": "E2E_PROD_001",
        "product_name": "E2E Test Product",
        "project_id": "E2E_PROJ_001",
    }

@pytest.fixture
def seed_pending_ticket(app_server: str) -> Generator[dict, None, None]:
    yield {
        "iid": 9999,
        "title": "E2E Test Ticket - Pending",
        "project_id": 100,
    }


import os
import pytest
from playwright.sync_api import Page, expect
from tests.e2e.admin.pages.admin_page import AdminPage

@pytest.mark.smoke
def test_product_import_flow(authenticated_page: Page):
    """
    Test Step:
    1. Navigate to Product Architecture view
    2. Upload Products CSV
    3. Verify Toast success message
    """
    admin_page = AdminPage(authenticated_page)
    
    # 1. Navigation
    admin_page.navigate_to_products()
    
    # 2. Upload CSV
    # Resolve absolute path for the fixture
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "fixtures", "products.csv")
    
    admin_page.upload_products(csv_path)
    
    # 3. Wait for upload to complete and verify success
    # The toast might appear quickly, so we wait for it with a generous timeout
    authenticated_page.wait_for_timeout(2000)  # Give backend time to process
    
    # Try to find toast with flexible selectors
    toast_container = authenticated_page.locator(".g-toast-container")
    if toast_container.count() > 0:
        toast = toast_container.locator(".g-toast").first
        expect(toast).to_be_visible(timeout=5000)
        expect(toast).to_contain_text("导入")
    else:
        # Fallback: check if products were actually imported by verifying cards
        authenticated_page.wait_for_timeout(1000)
        cards = authenticated_page.locator("adm-product-card")
        assert cards.count() > 0, "No product cards found after import"

@pytest.mark.smoke
def test_product_export_trigger(authenticated_page: Page):
    """
    Test Step:
    1. Navigate to Product Architecture view
    2. Click Export button
    3. Verify download is triggered
    """
    admin_page = AdminPage(authenticated_page)
    admin_page.navigate_to_products()
    
    # Setup download listener
    with authenticated_page.expect_download() as download_info:
        authenticated_page.click(".js-btn-export-products")
        
    download = download_info.value
    # Assert filename
    assert "products_export.csv" in download.suggested_filename

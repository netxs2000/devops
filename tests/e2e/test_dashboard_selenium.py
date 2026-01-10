
import os
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuration
DASHBOARD_URL = "http://localhost:8501"
PAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "dashboard", "pages")

def get_page_names():
    """Extract expected page names from the filesystem."""
    pages = []
    files = [f for f in os.listdir(PAGES_DIR) if f.endswith(".py")]
    # Sort files based on the prefix number to match Streamlit's sidebar order
    files.sort(key=lambda f: int(f.split("_")[0]) if f.split("_")[0].isdigit() else 999)
    
    for f in files:
        # Check if it follows the pattern '1_Name.py'
        match = re.match(r"(\d+)_+(.+)\.py", f)
        if match:
            # Streamlit replaces underscores with spaces in the sidebar
            page_name = match.group(2).replace("_", " ")
            pages.append(page_name)
    return pages

def run_test():
    page_names = get_page_names()
    print(f"Discovered {len(page_names)} pages to test: {page_names}")
    
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Try to initialize WebDriver
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"Failed to initialize Chrome Driver: {e}")
        print("Ensure you have Chrome and matching ChromeDriver installed.")
        return

    try:
        print(f"Navigating to {DASHBOARD_URL}...")
        driver.get(DASHBOARD_URL)
        time.sleep(5)  # Wait for initial load
        
        results = {}
        
        # Streamlit Sidebar Navigation
        # Locate all links in the sidebar. Streamlit sidebar items are often <li><a>...</a></li> or similar.
        # We will try to find links by text.
        
        for page_name in page_names:
            print(f"Testing module: [{page_name}]...", end=" ", flush=True)
            try:
                # Find link by partial text match because sometimes there are icons
                # Streamlit v1.x usually puts sidebar nav in a list
                link = None
                links = driver.find_elements(By.XPATH, "//div[@data-testid='stSidebarNav']//a")
                
                for l in links:
                    if page_name in l.text:
                        link = l
                        break
                
                if not link:
                    print(f"Link not found in sidebar")
                    results[page_name] = "SKIPPED (Link not found)"
                    continue
                
                link.click()
                
                # Wait for the page to settle.
                # We can check if the 'running' status is gone, but a simple sleep is often more robust for simple scripts.
                time.sleep(3)
                
                # Check for errors
                # Streamlit displays errors in elements with class 'stException' or text containing 'Traceback'
                errors = driver.find_elements(By.CLASS_NAME, "stException")
                error_texts = []
                if not errors:
                    # Also check for standard error alerts
                    alerts = driver.find_elements(By.XPATH, "//div[contains(@class, 'stAlert')]")
                    for alert in alerts:
                        # Filter for actual errors (red boxes), usually containing specific icons or styles
                        # This is a bit heuristic.
                        text = alert.text
                        if "Error" in text or "Traceback" in text or "KeyError" in text:
                             error_texts.append(text)
                else:
                    for err in errors:
                        error_texts.append(err.text)

                if error_texts:
                    print(f"FAILED")
                    print(f"   Errors found: {error_texts[:2]}") # Print first 2 errors
                    results[page_name] = "FAILED"
                else:
                    print(f"PASS")
                    results[page_name] = "PASS"
                    
            except Exception as ex:
                print(f"ERROR: {ex}")
                results[page_name] = f"ERROR: {str(ex)}"
        
        print("\n" + "="*40)
        print("Test Summary")
        print("="*40)
        passed = 0
        for name, status in results.items():
            icon = "[PASS]" if status == "PASS" else "[FAIL]"
            print(f"{icon} {name}: {status}")
            if status == "PASS":
                passed += 1
        
        print("-" * 40)
        print(f"Total: {len(results)}, Passed: {passed}, Failed: {len(results) - passed}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_test()

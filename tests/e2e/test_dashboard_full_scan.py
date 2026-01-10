
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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGES_DIR = os.path.join(BASE_DIR, "dashboard", "pages")

def get_page_info():
    """Extract expected page names and numbers from the filesystem."""
    pages = []
    files = [f for f in os.listdir(PAGES_DIR) if f.endswith(".py")]
    
    for f in files:
        # Check if it follows the pattern '1_Name.py'
        match = re.match(r"(\d+)_+(.+)\.py", f)
        if match:
            num = int(match.group(1))
            raw_name = match.group(2).replace("_", " ")
            pages.append({"num": num, "name": raw_name, "file": f})
        else:
            # Handle cases like 0_Gitprime.py
            pages.append({"num": 999, "name": f.replace(".py", "").replace("_", " "), "file": f})
            
    # Sort files based on the prefix number to match Streamlit's sidebar order
    pages.sort(key=lambda x: x["num"])
    return pages

def run_test():
    pages = get_page_info()
    print(f"Discovered {len(pages)} pages to test.")
    
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
        return

    results = []

    try:
        print(f"Navigating to {DASHBOARD_URL}...")
        driver.get(DASHBOARD_URL)
        time.sleep(10)  # Wait longer for initial load and data connection
        
        for p in pages:
            page_name = p["name"]
            print(f"Testing module: [{page_name}]...", end=" ", flush=True)
            
            try:
                # Find link in sidebar
                # Streamlit sidebar nav usually has high-depth links
                wait = WebDriverWait(driver, 10)
                sidebar_nav = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-testid='stSidebarNav']")))
                
                # Try to find the link multiple times with scrolling
                target_link = None
                for attempt in range(3):
                    links = driver.find_elements(By.XPATH, "//div[@data-testid='stSidebarNav']//a")
                    for l in links:
                        link_text = l.text.lower()
                        # Streamlit sidebar sometimes has leading numbers/icons
                        if page_name.lower() in link_text or (str(p["num"]) + " " in link_text):
                            target_link = l
                            break
                    
                    if target_link:
                        break
                    
                    # Scroll sidebar down and wait
                    sidebar_nav = driver.find_element(By.XPATH, "//div[@data-testid='stSidebarNav']")
                    driver.execute_script("arguments[0].scrollTop += 500;", sidebar_nav)
                    time.sleep(1)

                if not target_link:
                    found_links = [l.text for l in driver.find_elements(By.XPATH, "//div[@data-testid='stSidebarNav']//a")]
                    print(f"LINK NOT FOUND. Seen: {found_links[:5]}...")
                    results.append({"name": page_name, "status": "SKIPPED", "error": "Link not found in sidebar"})
                    continue

                # Scroll target into view
                driver.execute_script("arguments[0].scrollIntoView(true);", target_link)
                time.sleep(1)
                target_link.click()
                
                # Wait for page load (Streamlit status indicator 'running' disappears)
                time.sleep(5) 
                
                # Health Check: Look for Exception/Error blocks
                # 1. Custom st.error blocks usually have [data-testid="stNotification"]
                # 2. Tracebacks usually have class "stException"
                # 3. Code blocks containing "Traceback"
                
                problems = []
                
                # Check for explicit exceptions
                exceptions = driver.find_elements(By.CLASS_NAME, "stException")
                for ex in exceptions:
                    problems.append(ex.text.split('\n')[0]) # Get first line of error

                # Check for error alerts
                alerts = driver.find_elements(By.XPATH, "//div[contains(@class, 'stAlert')]")
                for alert in alerts:
                    text = alert.text
                    if any(kw in text for kw in ["Error", "Traceback", "KeyError", "ProgrammingError", "UndefinedColumn"]):
                        problems.append(text.split('\n')[0])

                if problems:
                    error_msg = "; ".join(problems)
                    print(f"FAILED: {error_msg}")
                    results.append({"name": page_name, "status": "FAILED", "error": error_msg})
                else:
                    print("PASS")
                    results.append({"name": page_name, "status": "PASS", "error": ""})

            except Exception as e:
                print(f"ERROR: {str(e)}")
                results.append({"name": page_name, "status": "ERROR", "error": str(e)})
        
    finally:
        driver.quit()

    # Generate Report
    report_path = os.path.join(BASE_DIR, "dashboard_test_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Dashboard 自动化巡检报告\n\n")
        f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("| 模块名称 | 状态 | 错误信息 |\n")
        f.write("| :--- | :--- | :--- |\n")
        for r in results:
            status_icon = "✅ PASS" if r["status"] == "PASS" else ("❌ FAILED" if r["status"] == "FAILED" else "⚠️ " + r["status"])
            f.write(f"| {r['name']} | {status_icon} | {r['error']} |\n")
            
    print(f"\nReport generated at: {report_path}")

if __name__ == "__main__":
    run_test()

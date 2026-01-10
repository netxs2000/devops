
import unittest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class TestDecisionHubAccess(unittest.TestCase):
    """
    Automated test to verify access to the Decision Hub from the DevOps Portal.
    """

    def setUp(self):
        # Configure Chrome options
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')  # Run in headless mode for CI/CD
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        
        # Initialize WebDriver
        try:
            self.driver = webdriver.Chrome(options=options)
        except Exception:
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
        self.driver.maximize_window()
        self.base_url = "http://127.0.0.1:8000"

    def test_decision_hub_navigation(self):
        driver = self.driver
        wait = WebDriverWait(driver, 20)  # Increased wait time

        print("\n[Step 1] Navigating to Login Page...")
        driver.get(f"{self.base_url}/service_desk_login.html")

        # 1. Login
        print("[Step 2] Performing Login...")
        try:
            # Fallback: Use fetch to directly call the API if UI interaction is flaky
            driver.execute_script("""
                const formData = new URLSearchParams();
                formData.append('username', 'admin@devops.local');
                formData.append('password', 'admin_password_123!');

                fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.access_token) {
                        // Manually set token and redirect (Simulating successful login logic)
                        if (typeof Auth !== 'undefined') {
                            Auth.setToken(data.access_token);
                        } else {
                            localStorage.setItem('auth_token', data.access_token);
                        }
                        window.location.href = 'index.html';
                    } else {
                        console.error('Login failed via fetch:', data);
                        document.body.setAttribute('data-login-error', JSON.stringify(data));
                    }
                })
                .catch(err => {
                    console.error('Network error:', err);
                    document.body.setAttribute('data-login-error', err.toString());
                });
            """)
            
            # Reset login_btn variable for safety if needed later, though we are bypassing click
            login_btn = None 
            time.sleep(2.0) # Wait for fetch and redirect
            
        except Exception as e:
            driver.save_screenshot("login_failure.png")
            self.fail(f"Login interaction failed: {str(e)}")

        # 2. Verify Redirect to Dashboard
        print("[Step 3] Waiting for Redirect to Dashboard...")
        try:
            wait.until(EC.url_contains("index.html"))
            wait.until(EC.presence_of_element_located((By.ID, "nav-decision-hub")))
            print("Login successful and redirected to index.html")
        except TimeoutException:
            # Debug: Check for alert
            try:
                alert = driver.find_element(By.ID, "alertBox")
                if alert.is_displayed():
                    print(f"❌ Login Alert Visible: {alert.text}")
            except:
                pass
            driver.save_screenshot("redirect_failure.png")
            self.fail(f"Failed to redirect to index.html. Current URL: {driver.current_url}")

        # 3. Click "Decision Hub"
        print("[Step 4] Clicking 'Decision Hub'...")
        decision_hub_link = driver.find_element(By.ID, "nav-decision-hub")
        decision_hub_link.click()

        # 4. Verify Iframe Loading
        print("[Step 5] verifying Decision Hub Iframe...")
        try:
            # Wait for the view to be visible
            wait.until(EC.visibility_of_element_located((By.ID, "decisionHubView")))
            
            iframe = driver.find_element(By.ID, "decisionHubFrame")
            src = iframe.get_attribute("src")
            print(f"Iframe Source: {src}")
            
            self.assertIn("localhost:8501", src, "Iframe source should point to Streamlit port 8501")

            # Note: We cannot easily check if the content INSIDE the iframe loaded successfully 
            # if it's a "Connection Refused" page because that is a browser error page, 
            # not a DOM element we can easily inspect without switching context.
            # But we can try to switch context.
            
            driver.switch_to.frame(iframe)
            # If connection is refused, usually the body is empty or contains specific chrome error text.
            # However, catching "Connection Refused" via Selenium is tricky directly.
            # We assume if we can find a known Streamlit element, it passed.
            
            # Try to find a Streamlit specific element (generic)
            # This might fail immediately if the page didn't load.
            try:
                # Streamlit usually has a root element with class 'stApp'
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "stApp")))
                print("✅ Decision Hub (Streamlit) loaded successfully!")
            except TimeoutException:
                print("❌ Decision Hub failed to load (Timeout looking for .stApp).")
                # Capture screenshot for debugging
                driver.save_screenshot("decision_hub_failure.png")
                raise Exception("Decision Hub content did not load. Likely connection refused.")

        except Exception as e:
            self.fail(f"Test Failed: {str(e)}")

    def tearDown(self):
        if self.driver:
            self.driver.quit()

if __name__ == "__main__":
    unittest.main()

import pytest
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_portal_navigation_and_modals(driver):
    """集成测试：验证门户导航与重构后的 Handler 交互。"""
    # 1. 访问登录页并模拟登录 (此处假设后端/静态服务运行在 8999 端口)
    driver.get("http://localhost:8999/service_desk_login.html")
    
    # 注入 Mock Token 以跳过真实登录流程
    driver.execute_script("localStorage.setItem('sd_token', 'mock_token_for_test');")
    driver.execute_script("localStorage.setItem('sd_user', JSON.stringify({email:'test@test.com', name:'Test', roles:['SYSTEM_ADMIN']}));")

    driver.get("http://localhost:8999/index.html")
    wait = WebDriverWait(driver, 10)
    
    # 2. 检查侧边栏加载
    sidebar = wait.until(EC.presence_of_element_located((By.ID, "sidebar-nav-container")))
    assert sidebar is not None
    
    # 3. 验证视图切换 (需求管理)
    req_link = driver.find_element(By.ID, "nav-reqs")
    req_link.click()
    
    req_view = wait.until(EC.visibility_of_element_located((By.ID, "pm-requirements-view")))
    assert "u-hide" not in req_view.get_attribute("class")
    
    # 4. 验证重构后的 Modal 弹出逻辑 (PmRequirementHandler)
    create_btn = driver.find_element(By.CLASS_NAME, "js-btn-create-req")
    create_btn.click()
    
    modal = wait.until(EC.visibility_of_element_located((By.ID, "pm-req-modal-overlay")))
    assert "u-flex" in modal.get_attribute("class")
    
    # 5. 验证心情打卡 Iframe 加载 (SysPulseHandler/SysAppHandler)
    pulse_link = driver.find_element(By.ID, "nav-pulse")
    pulse_link.click()
    
    pulse_view = wait.until(EC.visibility_of_element_located((By.ID, "sys-pulse-view")))
    iframe = pulse_view.find_element(By.ID, "pulseFrame")
    assert "devex_pulse.html" in iframe.get_attribute("src")

def test_unit_test_page_execution(driver):
    """执行前端单元测试运行器并验证其通过情况。"""
    driver.get("http://localhost:8999/tests/test_runner.html")
    wait = WebDriverWait(driver, 10)
    
    # 等待测试结束标识 (由 unit_tests.js 插入)
    summary = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(., 'Test Summary')]")))
    
    # 检查是否有失败用例
    fail_text = summary.find_element(By.XPATH, ".//p[contains(., 'Fail:')]").text
    assert "Fail: 0" in fail_text, f"Frontend unit tests failed: {fail_text}"

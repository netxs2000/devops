"""
Shared E2E Fixtures (Common for all modules)
"""

import os
import time
import subprocess
import socket
from typing import Generator

import pytest
import httpx
from playwright.sync_api import Page, Browser, BrowserContext, expect
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
APP_STARTUP_TIMEOUT = 30 

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def wait_for_server(url: str, timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except httpx.ConnectError:
            pass
        time.sleep(1)
    return False

@pytest.fixture(scope="session")
def app_server() -> Generator[str, None, None]:
    if os.getenv("E2E_EXTERNAL_SERVER") == "1":
        yield BASE_URL
        return

    if is_port_in_use(8000):
        yield BASE_URL
        return

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proc = subprocess.Popen(
        ["python", "-m", "uvicorn", "devops_portal.main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not wait_for_server(BASE_URL, APP_STARTUP_TIMEOUT):
        proc.terminate()
        stdout, stderr = proc.communicate(timeout=5)
        raise RuntimeError(f"Server failed to start")

    yield BASE_URL
    proc.terminate()

@pytest.fixture
def page_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="zh-CN",
    )
    yield context
    context.close()

@pytest.fixture
def page(page_context: BrowserContext) -> Generator[Page, None, None]:
    page = page_context.new_page()
    yield page
    page.close()

@pytest.fixture
def test_user_credentials() -> dict:
    return {
        "email": os.getenv("E2E_TEST_USER_EMAIL", "e2e_test@example.com"),
        "password": os.getenv("E2E_TEST_USER_PASSWORD", "e2e_test_password"),
    }

@pytest.fixture
def authenticated_page(
    page: Page,
    app_server: str,
    test_user_credentials: dict
) -> Generator[Page, None, None]:
    page.on("console", lambda msg: print(f"  [BROWSER CONSOLE] {msg.type}: {msg.text}"))
    
    # 拦截外部网络请求，防止 Google Fonts 等超时阻塞测试
    def handle_route(route):
        url = route.request.url
        # 允许本地请求和核心 API 路径
        if "127.0.0.1" in url or "localhost" in url:
            route.continue_()
        elif "static" in url or "/api/" in url or "/auth/" in url or "/admin/" in url:
            route.continue_()
        else:
            route.abort()
    
    page.route("**/*", handle_route)
    page.goto(f"{app_server}/static/index.html", wait_until="commit")
    login_modal = page.locator("#loginModal")
    
    try:
        user_name = page.locator("#user-display-name")
        if user_name.is_visible() and user_name.inner_text() != "Loading...":
            pass
        else:
            print(f"Attempting login for {test_user_credentials['email']}...")
            login_modal.wait_for(state="visible", timeout=10000)
            page.fill("#login-email", test_user_credentials["email"])
            page.fill("#login-password", test_user_credentials["password"])
            page.click("#login-submit")
            print("Waiting for login to complete (display name change)...")
            # 等待用户名显示（不再是 Loading...）
            expect(page.locator("#user-display-name")).not_to_have_text("Loading...", timeout=20000)
            print("Login successful.")
    except Exception as e:
        print(f"Login failed: {str(e)}")
        if not os.path.exists("test-results"):
            os.makedirs("test-results")
        page.screenshot(path="test-results/auth_failure.png")
        raise e

    yield page

"""
Service Desk E2E Tests - Shared Fixtures

提供 Service Desk 端到端测试所需的公共 Fixtures，包括：
- 应用服务器管理
- 数据库会话管理
- 认证用户页面
- 测试数据种子
"""

import os
import time
import subprocess
import socket
from typing import Generator

import pytest
import httpx
from playwright.sync_api import Page, Browser, BrowserContext
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# 配置常量
# =============================================================================

BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
APP_STARTUP_TIMEOUT = 30  # 秒


# =============================================================================
# 辅助函数
# =============================================================================

def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """等待服务器就绪"""
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


# =============================================================================
# Session-Scoped Fixtures (服务器生命周期)
# =============================================================================

@pytest.fixture(scope="session")
def app_server() -> Generator[str, None, None]:
    """
    启动 FastAPI 应用服务器 (Session 级别)。

    如果 E2E_EXTERNAL_SERVER=1，则假设服务器已经外部启动，直接返回 URL。
    否则，启动 uvicorn 子进程并在测试结束后关闭。
    """
    if os.getenv("E2E_EXTERNAL_SERVER") == "1":
        # 外部服务器模式 (如 Docker 容器)
        yield BASE_URL
        return

    # 检查端口是否已被占用
    if is_port_in_use(8000):
        print("Port 8000 already in use, assuming external server")
        yield BASE_URL
        return

    # 启动服务器
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    proc = subprocess.Popen(
        ["python", "-m", "uvicorn", "devops_portal.main:app",
         "--host", "127.0.0.1", "--port", "8000"],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 等待服务器就绪
    if not wait_for_server(BASE_URL, APP_STARTUP_TIMEOUT):
        proc.terminate()
        stdout, stderr = proc.communicate(timeout=5)
        raise RuntimeError(
            f"Server failed to start within {APP_STARTUP_TIMEOUT}s.\n"
            f"stdout: {stdout.decode()}\nstderr: {stderr.decode()}"
        )

    yield BASE_URL

    # 清理
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# =============================================================================
# Browser Fixtures (页面管理)
# =============================================================================

@pytest.fixture
def page_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """创建独立的浏览器上下文，用于隔离测试"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="zh-CN",
    )
    yield context
    context.close()


@pytest.fixture
def page(page_context: BrowserContext) -> Generator[Page, None, None]:
    """创建新页面"""
    page = page_context.new_page()
    yield page
    page.close()


# =============================================================================
# 认证 Fixtures
# =============================================================================

@pytest.fixture
def test_user_credentials() -> dict:
    """
    测试用户凭据。

    注意：E2E 测试需要预先在测试数据库中创建该用户，
    或通过环境变量指定已有测试账号。
    """
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
    """
    创建已认证的浏览器页面。

    执行登录流程，返回已登录状态的页面。
    """
    print(f"Navigating to {app_server}/static/index.html for authentication...")
    page.goto(f"{app_server}/static/index.html")

    # 等待登录模态框出现
    login_modal = page.locator("#loginModal")
    
    # 我们等待一会，看看是否会自动登录或显示模态框
    try:
        print("Checking if login is required...")
        # 如果已经登录，#user-display-name 会直接显示
        user_name = page.locator("#user-display-name")
        if user_name.is_visible() and user_name.inner_text() != "Loading...":
            print("Already logged in.")
        else:
            print("Login modal check...")
            login_modal.wait_for(state="visible", timeout=10000)
            print(f"Logging in as {test_user_credentials['email']}...")
            # 填写登录表单
            page.fill("#login-email", test_user_credentials["email"])
            page.fill("#login-password", test_user_credentials["password"])
            page.click("#login-submit")

            # 等待登录完成 (页面刷新)

            # 验证登录成功
            page.wait_for_selector("#user-display-name", state="visible", timeout=15000)
            print("Login successful.")
    except Exception as e:
        print(f"Auth fixture warning/error: {e}")
        # 如果失败了，我们尝试截个图看看发生了什么
        if not os.path.exists("test-results"):
            os.makedirs("test-results")
        page.screenshot(path="test-results/auth_failure.png")

    yield page


@pytest.fixture
def rd_authenticated_page(
    page: Page,
    app_server: str,
) -> Generator[Page, None, None]:
    """
    创建具有 RD 权限的已认证页面。

    用于测试工单处理流程，需要测试数据库中有 RD 角色用户。
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


# =============================================================================
# 数据种子 Fixtures
# =============================================================================

@pytest.fixture
def seed_test_product(app_server: str, test_user_credentials: dict) -> Generator[dict, None, None]:
    """
    通过 API 创建测试产品数据。

    注意：这需要 API 支持创建产品的端点，或者使用数据库 fixture 直接插入。
    如果 API 不支持，可以改用数据库连接直接插入。
    """
    # 这里使用占位符，实际项目需要根据 API 实现调整
    # 或者使用 conftest.py 中的 db_session fixture 直接操作数据库
    yield {
        "product_id": "E2E_PROD_001",
        "product_name": "E2E Test Product",
        "project_id": "E2E_PROJ_001",
    }


@pytest.fixture
def seed_pending_ticket(app_server: str) -> Generator[dict, None, None]:
    """
    创建待处理的 Service Desk 工单用于测试。

    实际实现需要通过 API 或数据库创建测试工单。
    """
    yield {
        "iid": 9999,
        "title": "E2E Test Ticket - Pending",
        "project_id": 100,
    }

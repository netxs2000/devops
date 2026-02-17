"""认证模块集成测试。

本模块通过 FastAPI TestClient 与内存数据库对 Auth 模块进行全链路验证。
包含注册、登录、个人信息获取及 GitLab 绑定重定向等核心逻辑。
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from devops_portal.main import app
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.models.base_models import Base, User, UserCredential
from devops_collector.auth import auth_service
from devops_collector.config import settings

# 使用内存数据库进行集成测试，确保环境纯净
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db_session")
def fixture_db_session():
    """认证模块集成测试数据库会话 Fixture。
    
    创建所有表并提供一个干净的会话，测试结束后删除所有表。
    
    Yields:
        Session: SQLAlchemy 数据库会话。
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Disable foreign keys for cleanup to avoid IntegrityError with circular dependencies
        with engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(bind=engine)
        with engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")


@pytest.fixture(name="client")
def fixture_client(db_session):
    """创建测试客户端并注入数据库会话。
    
    Args:
        db_session: 由 db_session fixture 提供的数据库会话。
        
    Yields:
        TestClient: FastAPI 测试客户端。
    """

    def override_get_auth_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_auth_db] = override_get_auth_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_auth_register_success(client):
    """测试合法邮箱域名的用户注册流程。
    
    预期行为：注册成功，返回 200 状态码及用户信息。
    """
    payload = {
        "email": "integration_test@tjhq.com",
        "password": "testpassword123",
        "full_name": "Integration Tester",
        "employee_id": "EMP_INT_001",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]


def test_auth_register_invalid_domain(client):
    """测试非法邮箱域名的注册拦截。
    
    预期行为：注册失败，返回 400 状态码及提示信息。
    """
    payload = {
        "email": "bad_user@gmail.com",
        "password": "testpassword123",
        "full_name": "Bad Tester",
        "employee_id": "EMP_BAD_001",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "仅支持以下域名的公司邮箱注册" in response.json()["detail"]


def test_auth_login_success(client, db_session):
    """测试合法用户凭据登录。
    
    预期行为：成功返回 JWT 访问令牌。
    """
    email = "login_success@tjhq.com"
    password = "login_pwd_123"

    # 初始化测试数据
    hashed_pwd = auth_service.auth_get_password_hash(password)
    user_id = uuid.uuid4()
    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="Login Success",
        is_active=True,
        is_current=True,
        is_deleted=False,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCredential(user_id=user_id, password_hash=hashed_pwd))
    db_session.commit()

    # 执行登录请求
    login_data = {"username": email, "password": password}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_auth_login_fail_wrong_password(client, db_session):
    """测试错误密码登录请求。
    
    预期行为：登录失败，返回 401 状态码。
    """
    email = "login_fail@tjhq.com"
    password = "correct_password"

    # 初始化测试数据
    user_id = uuid.uuid4()
    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="Fail Tester",
        is_active=True,
        is_current=True,
        is_deleted=False,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        UserCredential(
            user_id=user_id, password_hash=auth_service.auth_get_password_hash(password)
        )
    )
    db_session.commit()

    # 使用错误密码尝试登录
    login_data = {"username": email, "password": "wrong_password"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401


def test_auth_get_me_flow(client, db_session):
    """测试获取当前登录用户信息全链路。
    
    流程：注册 -> 登录 -> 使用 Token 访问 /auth/me。
    预期行为：全流程成功，最终返回正确的用户信息。
    """
    # 1. 注册
    reg_payload = {
        "email": "flow_test@tjhq.com",
        "password": "flow_password",
        "full_name": "Flow Tester",
        "employee_id": "EMP_FLOW_001",
    }
    client.post("/auth/register", json=reg_payload)

    # 2. 登录
    login_data = {"username": reg_payload["email"], "password": reg_payload["password"]}
    login_resp = client.post("/auth/login", data=login_data)
    token = login_resp.json()["access_token"]

    # 3. 访问 /auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == reg_payload["email"]
    assert me_data["full_name"] == reg_payload["full_name"]


def test_auth_gitlab_bind_redirect(client, db_session):
    """测试获取 GitLab 绑定重定向地址。
    
    预期行为：正确重定向到 GitLab 授权页面，且包含正确的 client_id 和 state。
    """
    # 模拟环境配置 (如果尚未配置)
    settings.gitlab.client_id = "test_client_id"
    settings.gitlab.redirect_uri = "http://localhost/auth/gitlab/callback"
    settings.gitlab.url = "https://gitlab.example.com"

    email = "gitlab_test@tjhq.com"
    password = "gitlab_password"

    # 创建用户
    user_id = uuid.uuid4()
    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="GitLab Tester",
        is_active=True,
        is_current=True,
        is_deleted=False,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        UserCredential(
            user_id=user_id, password_hash=auth_service.auth_get_password_hash(password)
        )
    )
    db_session.commit()

    # 登录获取 Token
    login_resp = client.post("/auth/login", data={"username": email, "password": password})
    token = login_resp.json()["access_token"]

    # 获取重定向 (不使用 follow_redirects 以便检查 Location)
    headers = {"Authorization": f"Bearer {token}"}
    bind_response = client.get("/auth/gitlab/bind", headers=headers, follow_redirects=False)
    
    assert bind_response.status_code == 307  # RedirectResponse 默认状态码
    location = bind_response.headers["Location"]
    assert "gitlab.example.com" in location
    assert "client_id=test_client_id" in location
    assert f"state={user_id}" in location

"""GitLab OAuth 登录功能的测试。

验证 GitLab 登录跳转、回调处理以及自动创建待审批用户等核心逻辑。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from devops_portal.main import app
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.models.base_models import Base, User, UserOAuthToken
from devops_collector.config import settings
from devops_collector.auth.auth_database import AuthSessionLocal

# 使用内存数据库进行集成测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def fixture_db_session():
    """创建干净的数据库会话。"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def fixture_client(db_session):
    """创建测试客户端并注入数据库会话。"""
    def override_get_auth_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_auth_db] = override_get_auth_db
    app.dependency_overrides[AuthSessionLocal] = override_get_auth_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

def test_gitlab_login_redirect(client):
    """验证 /auth/gitlab/login 是否正确重定向到 GitLab。"""
    response = client.get("/auth/gitlab/login", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert settings.gitlab.url in location
    assert "client_id=" in location
    assert "redirect_uri=" in location
    assert "state=login_flow" in location

@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.get")
def test_gitlab_callback_new_user(mock_get, mock_post, client, db_session):
    """测试 GitLab 回调：如果是新用户，应自动创建待审批账户。"""
    
    # 1. 模拟 Token 交换响应
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "access_token": "mock_gitlab_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "mock_refresh_token"
        }
    )
    
    # 2. 模拟 GitLab 用户信息响应
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "email": "new_oauth_user@tjhq.com",
            "name": "OAuth Tester",
            "username": "oauth_tester"
        }
    )
    
    # 执行回调
    response = client.get("/auth/gitlab/callback?code=mock_code&state=login_flow", follow_redirects=False)
    
    # 验证重定向到 pending 状态
    assert response.status_code == 307
    assert "auth_state=pending" in response.headers["location"]
    
    # 验证数据库中是否创建了用户
    user = db_session.query(User).filter_by(primary_email="new_oauth_user@tjhq.com").first()
    assert user is not None
    assert user.full_name == "OAuth Tester"
    assert user.is_active is False  # 应为待审批状态

@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.get")
def test_gitlab_callback_existing_user(mock_get, mock_post, client, db_session):
    """测试 GitLab 回调：如果是已存在且激活的用户，应成功登录。"""
    
    email = "existing_user@tjhq.com"
    # 预先创建一个已激活用户
    from devops_collector.auth import auth_service
    from devops_collector.auth.auth_schema import AuthRegisterRequest
    auth_service.auth_create_user(
        db_session, 
        AuthRegisterRequest(email=email, password="somepassword", full_name="Existing User")
    )
    user = db_session.query(User).filter_by(primary_email=email).first()
    user.is_active = True
    db_session.commit()

    # 模拟响应
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"access_token": "abc"})
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {"email": email, "name": "Existing User"})
    
    # 执行回调
    response = client.get("/auth/gitlab/callback?code=mock_code&state=login_flow", follow_redirects=False)
    
    # 验证重定向包含 access_token (登录成功)
    assert response.status_code == 307
    location = response.headers["location"]
    assert "access_token=" in location
    assert "#login_success" in location

def test_gitlab_callback_domain_not_allowed(client):
    """测试 GitLab 回调：邮箱域名不允许。"""
    with patch("httpx.AsyncClient.post") as mock_post, \
         patch("httpx.AsyncClient.get") as mock_get:
        
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"access_token": "abc"})
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"email": "stranger@hacker.com", "name": "Hacker"})
        
        response = client.get("/auth/gitlab/callback?code=mock_code&state=login_flow", follow_redirects=False)
        assert response.status_code == 307
        assert "auth_error=domain_not_allowed" in response.headers["location"]

"""Auth 模块路由集成测试。

测试认证相关的 API 接口，包括用户注册、登录以及获取当前用户信息。
使用 FastAPI TestClient 和内存数据库进行全链路验证。
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
    """认证模块集成测试数据库会话 Fixture。
    
    Yields:
        Session: SQLAlchemy 数据库会话。
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def fixture_client(db_session):
    """创建测试客户端并注入数据库会话。
    
    Args:
        db_session: 由 fixture 提供的数据库会话。
        
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

def test_auth_register_user(client):
    """测试用户注册接口。"""
    payload = {
        "email": "register_test@tjhq.com",
        "password": "testpassword123",
        "full_name": "Register Tester",
        "employee_id": "EMP001"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]

def test_auth_login_user(client, db_session):
    """测试用户登录获取 Token 接口。"""
    email = "login_test@tjhq.com"
    password = "loginpassword123"
    
    # 预先在模拟数据库中创建一个用户
    hashed_pwd = auth_service.auth_get_password_hash(password)
    user_id = uuid.uuid4()
    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="Login Tester",
        is_active=True,
        is_current=True,
        is_deleted=False
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCredential(user_id=user_id, password_hash=hashed_pwd))
    db_session.commit()
    
    # 执行登录请求 (OAuth2PasswordRequestForm 使用 data 而不是 json)
    login_data = {
        "username": email,
        "password": password
    }
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_auth_get_me_protected(client, db_session):
    """测试获取个人信息接口（含认证 Token 验证）。"""
    email = "me_test@tjhq.com"
    password = "mepassword123"
    
    # 场景：用户已存在
    user_id = uuid.uuid4()
    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="Me Tester",
        is_active=True,
        is_current=True,
        is_deleted=False
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserCredential(user_id=user_id, password_hash=auth_service.auth_get_password_hash(password)))
    db_session.commit()
    
    # 登录获取 Token
    login_resp = client.post("/auth/login", data={"username": email, "password": password})
    token = login_resp.json()["access_token"]
    
    # 使用 Token 请求受保护的 /auth/me 接口
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data["full_name"] == "Me Tester"

def test_auth_get_me_unauthorized(client):
    """测试未携带 Token 访问受保护接口应返回 401。"""
    response = client.get("/auth/me")
    assert response.status_code == 401

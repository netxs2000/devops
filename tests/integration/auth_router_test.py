"""认证模块路由集成测试。

测试认证相关的 API 接口，包括用户注册、登录以及获取当前用户信息。
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from devops_portal.main import app
from devops_collector.auth.router import get_db
from devops_collector.models.base_models import Base, User, UserCredential
from devops_collector.auth import services

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
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

def test_register_user(client):
    """测试用户注册接口。"""
    payload = {
        "email": "register_test@example.com",
        "password": "testpassword123",
        "full_name": "Register Tester",
        "employee_id": "EMP001"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]

def test_login_user(client, db_session):
    """测试用户登录接口。"""
    email = "login_test@example.com"
    password = "loginpassword123"
    
    # 预先创建一个用户
    hashed_pwd = services.get_password_hash(password)
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
    
    # 执行登录
    login_data = {
        "username": email,
        "password": password
    }
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_me_protected(client, db_session):
    """测试获取个人信息接口（含认证）。"""
    email = "me_test@example.com"
    password = "mepassword123"
    
    # 注册并登录获取 Token
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
    db_session.add(UserCredential(user_id=user_id, password_hash=services.get_password_hash(password)))
    db_session.commit()
    
    # 获取 Token
    response = client.post("/auth/login", data={"username": email, "password": password})
    token = response.json()["access_token"]
    
    # 使用 Token 请求 /auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data["full_name"] == "Me Tester"

def test_get_me_unauthorized(client):
    """测试未授权访问受保护接口。"""
    response = client.get("/auth/me")
    assert response.status_code == 401

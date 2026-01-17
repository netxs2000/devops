"""认证模块逻辑单元测试。

测试包括密码哈希验证、用户认证核心逻辑以及 JWT 令牌生成。
"""
import uuid
from datetime import timedelta
import pytest
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.auth import auth_service as services
from devops_collector.models.base_models import Base, User, UserCredential

# 使用内存数据库进行单元测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
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
        # Disable foreign keys for cleanup to avoid IntegrityError with circular dependencies
        with engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        Base.metadata.drop_all(bind=engine)
        with engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")

def test_password_hashing():
    """测试密码哈希生成与校验。"""
    password = "test_password_123"
    hashed = services.auth_get_password_hash(password)
    assert hashed != password
    assert services.auth_verify_password(password, hashed) is True
    assert services.auth_verify_password("wrong_password", hashed) is False

def test_create_access_token():
    """测试 JWT 访问令牌生成。"""
    data = {"sub": "test@example.com", "user_id": str(uuid.uuid4())}
    token = services.auth_create_access_token(data, expires_delta=timedelta(minutes=15))
    
    # 验证令牌内容
    payload = jwt.decode(token, services.SECRET_KEY, algorithms=[services.ALGORITHM])
    assert payload["sub"] == data["sub"]
    assert payload["user_id"] == data["user_id"]
    assert "exp" in payload

def test_authenticate_user_success(db_session):
    """测试用户认证成功场景。"""
    email = "auth_test@example.com"
    password = "secure_password"
    
    # 手动创建测试用户
    user_id = uuid.uuid4()
    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="Auth Test User",
        is_active=True,
        is_current=True,
        is_deleted=False
    )
    db_session.add(user)
    db_session.flush()
    
    cred = UserCredential(
        user_id=user_id,
        password_hash=services.auth_get_password_hash(password)
    )
    db_session.add(cred)
    db_session.commit()
    
    # 执行认证测试
    authenticated_user = services.auth_authenticate_user(db_session, email, password)
    assert authenticated_user is not False
    assert authenticated_user.primary_email == email

def test_authenticate_user_failure(db_session):
    """测试用户认证失败场景。"""
    email = "fail_test@example.com"
    password = "correct_password"
    
    # 场景 1: 用户不存在
    assert services.auth_authenticate_user(db_session, "none@example.com", password) is False
    
    # 注册用户
    user_id = uuid.uuid4()
    user = User(
        global_user_id=user_id,
        primary_email=email,
        is_active=True,
        is_current=True,
        is_deleted=False
    )
    db_session.add(user)
    db_session.flush()
    
    # 场景 2: 密码错误
    cred = UserCredential(
        user_id=user_id,
        password_hash=services.auth_get_password_hash(password)
    )
    db_session.add(cred)
    db_session.commit()
    
    assert services.auth_authenticate_user(db_session, email, "wrong_password") is False

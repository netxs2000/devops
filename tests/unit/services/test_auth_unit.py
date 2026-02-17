"""Auth 模块核心逻辑单元测试。

验证密码加密、JWT 令牌生成以及用户认证核心服务的正确性。
"""
import uuid
from datetime import timedelta
import pytest
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.auth import auth_service
from devops_collector.models.base_models import Base, User, UserCredential
from devops_collector.config import settings

# 使用内存数据库进行单元测试，确保测试环境隔离
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def fixture_db_session():
    """单元测试数据库会话 Fixture。
    
    创建所有表并在测试结束后清理数据库。
    
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

def test_auth_password_hashing():
    """测试密码哈希生成与校验功能。"""
    password = "test_password_123"
    hashed = auth_service.auth_get_password_hash(password)
    assert hashed != password
    assert auth_service.auth_verify_password(password, hashed) is True
    assert auth_service.auth_verify_password("wrong_password", hashed) is False

def test_auth_create_access_token():
    """测试 JWT 访问令牌的生成与解密验证。"""
    data = {"sub": "test@tjhq.com", "user_id": str(uuid.uuid4())}
    token = auth_service.auth_create_access_token(data, expires_delta=timedelta(minutes=15))
    
    # 验证令牌内容是否符合预期
    payload = jwt.decode(token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
    assert payload["sub"] == data["sub"]
    assert payload["user_id"] == data["user_id"]
    assert "exp" in payload

def test_auth_validate_email_domain():
    """测试电子邮箱域名过滤逻辑。"""
    # 确保配置中有预期的域名（通常由 settings 注入）
    original_domains = settings.auth.allowed_domains
    settings.auth.allowed_domains = ["tjhq.com", "mofit.com.cn"]
    
    try:
        assert auth_service.auth_validate_email_domain("user@tjhq.com") is True
        assert auth_service.auth_validate_email_domain("user@mofit.com.cn") is True
        assert auth_service.auth_validate_email_domain("user@gmail.com") is False
        assert auth_service.auth_validate_email_domain("invalid-email") is False
    finally:
        settings.auth.allowed_domains = original_domains

def test_auth_authenticate_user_success(db_session):
    """测试用户凭据认证成功场景。"""
    email = "auth_unit_test@tjhq.com"
    password = "secure_password"
    
    # 构建测试用户数据
    user_id = uuid.uuid4()
    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="Unit Tester",
        is_active=True,
        is_current=True,
        is_deleted=False
    )
    db_session.add(user)
    db_session.flush()
    
    cred = UserCredential(
        user_id=user_id,
        password_hash=auth_service.auth_get_password_hash(password)
    )
    db_session.add(cred)
    db_session.commit()
    
    # 执行认证并检查结果
    authenticated_user = auth_service.auth_authenticate_user(db_session, email, password)
    assert authenticated_user is not False
    assert authenticated_user.primary_email == email

def test_auth_authenticate_user_failure(db_session):
    """测试用户认证失败（用户不存在或密码错误）场景。"""
    email = "fail_test@tjhq.com"
    password = "correct_password"
    
    # 1. 尝试认证不存在的用户
    assert auth_service.auth_authenticate_user(db_session, "nonexistent@tjhq.com", password) is False
    
    # 2. 注册用户但输入错误密码
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
    
    cred = UserCredential(
        user_id=user_id,
        password_hash=auth_service.auth_get_password_hash(password)
    )
    db_session.add(cred)
    db_session.commit()
    
    assert auth_service.auth_authenticate_user(db_session, email, "wrong_password") is False

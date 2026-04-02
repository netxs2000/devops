"""tests/unit/portal 共享 fixtures。

提供基于唯一物理数据库文件的 portal 测试环境。
"""

import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from devops_collector.auth.auth_database import get_auth_db
from devops_collector.models.base_models import Base, SysRole, User, UserRole
from devops_portal.dependencies import get_current_user
from devops_portal.main import app


@pytest.fixture(scope="function")
def portal_db():
    """每个 Portal 测试用例独立的物理数据库环境。"""
    # 1. 唯一物理文件路径配置
    db_fd, db_path = tempfile.mkstemp(suffix=".db", prefix="portal_test_")
    os.close(db_fd)
    db_uri = f"sqlite:///{db_path}"

    # 2. 同步环境变量 (关键)
    os.environ["DB_URI"] = db_uri
    os.environ["GITLAB_URL"] = "https://gitlab.example.com"
    os.environ["GITLAB_TOKEN"] = "testtoken"
    os.environ["JWT_SECRET_KEY"] = "testsecret"
    os.environ["JWT_ALGORITHM"] = "HS256"

    # 3. 创建 Engine 与会话工厂
    engine = create_engine(
        db_uri,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

    db = SessionLocal()

    try:
        yield db, engine, db_uri
    finally:
        db.close()
        # 物理清理
        with engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
            Base.metadata.drop_all(bind=conn)
        engine.dispose()

        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass


@pytest.fixture(scope="function")
def db_session(portal_db):
    """提供 db_session 夹具，兼容旧测试。

    关键：所有依赖 portal_db 的 fixture (client / authenticated_client / db_session)
    共享同一个 portal_db 实例，因此操作的是同一个物理数据库和会话。
    """
    db, engine, db_uri = portal_db
    return db


@pytest.fixture(scope="function")
def client(portal_db):
    """带独立 DB 实例的 TestClient，注入依赖重写。"""
    db, engine, db_uri = portal_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_auth_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def mock_user(portal_db):
    """创建一个带 SYSTEM_ADMIN 角色的真实 User 对象并持久化到测试数据库。

    - 使用固定邮箱 test@example.com，兼容 test_admin_router 等硬编码引用。
    - 默认赋予 SYSTEM_ADMIN 角色，使权限校验 (PermissionRequired/RoleRequired) 放行。
    """
    db, engine, db_uri = portal_db

    user = User(
        global_user_id=uuid.uuid4(),
        employee_id=f"EMP-{uuid.uuid4().hex[:8]}",
        username="test_user",
        full_name="Test User",
        primary_email="test@example.com",
        is_active=True,
        is_current=True,
    )
    db.add(user)
    db.flush()

    # 创建 SYSTEM_ADMIN 角色并关联
    admin_role = db.query(SysRole).filter(SysRole.role_key == "SYSTEM_ADMIN").first()
    if not admin_role:
        admin_role = SysRole(role_name="System Admin", role_key="SYSTEM_ADMIN", role_sort=0)
        db.add(admin_role)
        db.flush()

    user_role = UserRole(user_id=user.global_user_id, role_id=admin_role.id)
    db.add(user_role)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def authenticated_client(portal_db, mock_user):
    """带认证注入的 TestClient。

    在 client 基础上额外注入 get_current_user -> mock_user 依赖，
    使所有需要认证的路由端点可以通过依赖校验。
    """
    db, engine, db_uri = portal_db

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_auth_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

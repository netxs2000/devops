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
from devops_collector.models.base_models import Base, User
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
            except:
                pass

@pytest.fixture(scope="function")
def db_session(portal_db):
    """
    提供 db_session 夹具，兼容旧测试。
    """
    db, engine, db_uri = portal_db
    return db

@pytest.fixture(scope="function")
def client(portal_db):
    """
    带独立 DB 实例的 TestClient，注入依赖重写。
    """
    db, engine, db_uri = portal_db

    def override_get_db():
        try:
            # 这里必须确保使用与当前测试用例相同的物理库会话
            yield db
        finally:
            pass

    # 依赖重写注入 (针对 devops_collector.auth.auth_database)
    app.dependency_overrides[get_auth_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    # 清理注入
    app.dependency_overrides.clear()

"""tests/integration 共享集成测试 fixtures。

提供基于 SQLite 的 db_session 和 FastAPI TestClient，
供需要跨模块交互验证的集成测试使用。
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Mock environment variables BEFORE any other imports
os.environ.setdefault("DB_URI", "sqlite:///:memory:")
os.environ.setdefault("GITLAB_URL", "https://gitlab.example.com")
os.environ.setdefault("GITLAB_TOKEN", "testtoken")
os.environ.setdefault("JWT_SECRET_KEY", "testsecret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

from devops_collector.auth.auth_database import get_auth_db
from devops_collector.models.base_models import Base
from devops_portal.main import app


# --- REFACTORED FOR PERFORMANCE (Session-scoped Engine) ---
from sqlalchemy.pool import StaticPool
from sqlalchemy import event
from sqlalchemy.engine import Engine

SQLALCHEMY_DATABASE_URL = os.environ["DB_URI"]

_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once per session."""
    from devops_collector.models.base_models import Base
    # Import models to register with Base.metadata
    import devops_collector.models.base_models
    import devops_collector.models.mdm_organizations
    # ...
    Base.metadata.create_all(bind=_engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a nested transaction session for each test for speed & isolation."""
    connection = _engine.connect()
    transaction = connection.begin()
    session = _SessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a TestClient with a database session."""

    def override_get_auth_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_auth_db] = override_get_auth_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

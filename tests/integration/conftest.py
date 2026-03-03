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


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test using a temporary file."""
    db_file = f"test_{uuid.uuid4()}.db"
    db_url = f"sqlite:///{db_file}"

    _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False)

    Base.metadata.create_all(bind=_engine)
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
        _engine.dispose()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


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

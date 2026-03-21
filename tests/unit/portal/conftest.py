import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Mock environment variables BEFORE any other imports that might use them
os.environ["DB_URI"] = "sqlite:///:memory:"
os.environ["GITLAB_URL"] = "https://gitlab.example.com"
os.environ["GITLAB_TOKEN"] = "testtoken"
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["JWT_ALGORITHM"] = "HS256"

# Import after setting env vars
import uuid

from sqlalchemy.pool import StaticPool

from devops_collector.auth.auth_database import get_auth_db
from devops_collector.models.base_models import Base, User

# Import ServiceDeskTicket to register it with Base.metadata before create_all
from devops_portal.main import app


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once per session, ensuring all models are registered."""
    # Import all models to register them on the metadata
    Base.metadata.create_all(bind=_engine)
    return _engine


@pytest.fixture(scope="function")
def db_session(setup_database):
    """Create a nested transaction session for each test to ensure isolation & speed."""
    connection = setup_database.connect()
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


@pytest.fixture
def mock_user():
    """Create a mock user object with admin privileges."""

    u = User(
        global_user_id=uuid.uuid4(),
        primary_email="test@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True,
    )

    from devops_collector.models.base_models import SysRole

    u.roles = [SysRole(role_key="SYSTEM_ADMIN", role_name="System Admin")]
    # Note: don't add to session here, authenticated_client will do it
    return u


@pytest.fixture
def authenticated_client(client, db_session, mock_user, monkeypatch):
    """Create a client with an authenticated user and mocked RBAC."""
    from devops_collector.auth import auth_service
    from devops_collector.core import security
    from devops_portal import dependencies

    # Ensure user exists in DB
    db_session.add(mock_user)
    db_session.commit()

    token_payload = {
        "sub": mock_user.primary_email,
        "roles": [security.ADMIN_ROLE_KEY],
        "permissions": [security.ADMIN_PERMISSION_WILDCARD],
    }

    # Mock auth service functions globally
    monkeypatch.setattr(auth_service, "auth_decode_access_token", lambda t: token_payload if t == "mock-token" else None)

    def mock_get_current_user(db, t):
        if t == "mock-token":
            # RE-FETCH the user using the session passed to the dependency to avoid DetachedInstanceError
            return db.query(User).filter_by(primary_email=mock_user.primary_email).first()
        return None

    monkeypatch.setattr(auth_service, "auth_get_current_user", mock_get_current_user)

    # Override get_current_user for endpoints that use it directly
    app.dependency_overrides[dependencies.get_current_user] = lambda: db_session.query(User).filter_by(primary_email=mock_user.primary_email).first()

    client.headers["Authorization"] = "Bearer mock-token"
    yield client

    app.dependency_overrides.clear()

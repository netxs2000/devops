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
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.models.base_models import Base, User

# Import ServiceDeskTicket to register it with Base.metadata before create_all
from devops_portal.main import app


# Setup database in a more isolated way
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test using a temporary file."""
    import os
    import uuid

    db_file = f"test_{uuid.uuid4()}.db"
    db_url = f"sqlite:///{db_file}"

    _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    _TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False)

    # Create all tables
    Base.metadata.create_all(bind=_engine)
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        _engine.dispose()
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except:
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


@pytest.fixture
def mock_user():
    """Create a mock user object with admin privileges."""
    import uuid

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
    monkeypatch.setattr(
        auth_service, "auth_decode_access_token", lambda t: token_payload if t == "mock-token" else None
    )

    def mock_get_current_user(db, t):
        if t == "mock-token":
            # RE-FETCH the user using the session passed to the dependency to avoid DetachedInstanceError
            return db.query(User).filter_by(primary_email=mock_user.primary_email).first()
        return None

    monkeypatch.setattr(auth_service, "auth_get_current_user", mock_get_current_user)

    # Override get_current_user for endpoints that use it directly
    app.dependency_overrides[dependencies.get_current_user] = lambda: (
        db_session.query(User).filter_by(primary_email=mock_user.primary_email).first()
    )

    client.headers["Authorization"] = "Bearer mock-token"
    yield client

    app.dependency_overrides.clear()

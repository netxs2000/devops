import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Mock environment variables BEFORE any other imports that might use them
os.environ["DB_URI"] = "sqlite:///:memory:"
os.environ["GITLAB_URL"] = "https://gitlab.example.com"
os.environ["GITLAB_TOKEN"] = "testtoken"
os.environ["JWT_SECRET_KEY"] = "testsecret"
os.environ["JWT_ALGORITHM"] = "HS256"

# Import after setting env vars
from devops_collector.models.base_models import Base
from devops_portal.main import app
from devops_portal.dependencies import get_current_user
from devops_collector.models.base_models import User
from devops_collector.auth.auth_database import get_auth_db

# Setup in-memory SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Disable foreign keys for cleanup to avoid IntegrityError with circular dependencies
        with engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)
        with engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")

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
    """Create a mock user object."""
    import uuid
    u = User(
        global_user_id=uuid.uuid4(),
        primary_email="test@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True
    )
    u.roles = []
    return u

@pytest.fixture
def authenticated_client(client, mock_user):
    """Create a client with an authenticated user."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return client

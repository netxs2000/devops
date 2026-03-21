import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# Setup in-memory SQLite database
# Use check_same_thread=False for SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# --- REFACTORED FOR PERFORMANCE (Session-scoped Engine) ---
from sqlalchemy import event
from sqlalchemy.engine import Engine


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


_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once per session."""
    # Trigger full model registration via package import
    from devops_collector.models.base_models import Base

    Base.metadata.create_all(bind=_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a nested transaction session for each test to ensure isolation & speed."""
    connection = _engine.connect()
    transaction = connection.begin()
    session = _SessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

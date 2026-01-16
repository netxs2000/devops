import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup in-memory SQLite database
# Use check_same_thread=False for SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from devops_collector.models.base_models import Base

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Disable foreign keys for cleanup
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)
        
        # Re-enable foreign keys (though strictly engine-level listener handles new connections, 
        # this is for good measure if we reused connections, but we use StaticPool so...)
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")

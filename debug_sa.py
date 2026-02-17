
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup env
os.environ["DB_URI"] = "sqlite:///:memory:"
os.environ["GITLAB_URL"] = "https://gitlab.example.com"
os.environ["PYTHONPATH"] = "."

# Import things to test
sys.path.insert(0, os.getcwd())

try:
    from devops_portal.main import app
    from devops_collector.models.base_models import Base, User
    from tests.unit.devops_portal.conftest import engine, TestingSessionLocal
    
    print("Imports success")
    
    # Run a single test logic manually to see where it crashes
    db = TestingSessionLocal()
    Base.metadata.create_all(bind=engine)
    
    import uuid
    u = User(
        global_user_id=uuid.uuid4(),
        primary_email="test@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True
    )
    db.add(u)
    db.commit()
    print("User added and committed")
    
    # Simulate the router call
    users = db.query(User).all()
    print(f"Users in DB: {len(users)}")
    
    db.close()
    Base.metadata.drop_all(bind=engine)
    print("Cleanup success")

except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)

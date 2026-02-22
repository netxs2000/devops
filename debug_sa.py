
import os
import sys


# Setup env
os.environ["DB_URI"] = "sqlite:///:memory:"
os.environ["GITLAB_URL"] = "https://gitlab.example.com"
os.environ["PYTHONPATH"] = "."

# Import things to test
sys.path.insert(0, os.getcwd())

try:
    from tests.unit.devops_portal.conftest import TestingSessionLocal, engine

    from devops_collector.models.base_models import Base, User

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

except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)

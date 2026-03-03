import sys

# Assume the dev environment is running at localhost:8000
# And we have a valid token (requires login or mock)
# For now, let's just check the structure and if it's reachable in the container if possible.
# Actually, I'll run a python script that mocks the DB session and calls the service directly to verify the service logic.
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from devops_collector.core.admin_service import AdminService
from devops_collector.models.base_models import Base, OKRObjective, User


def test_preview_logic():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Setup mock data
    user = User(global_user_id=uuid.uuid4(), full_name="Admin", username="admin", primary_email="admin@test.com")
    session.add(user)
    session.flush()

    obj = OKRObjective(
        title="Test Objective", owner_id=user.global_user_id, period="2024-Q1", status="ACTIVE", progress=0.5
    )
    session.add(obj)
    session.commit()

    service = AdminService(session)
    results = service.list_okrs()

    print(f"Results count: {len(results)}")
    if len(results) > 0:
        print(f"First result: {results[0]['title']}, status: {results[0]['status']}, period: {results[0]['period']}")
        assert results[0]["owner_name"] == "Admin"
        assert results[0]["period"] == "2024-Q1"
    else:
        print("Error: No results found!")
        sys.exit(1)


if __name__ == "__main__":
    test_preview_logic()

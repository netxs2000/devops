import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, Organization
from devops_collector.core.business_auth import get_business_linked_roles

# Setup in-memory SQLite
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

try:
    user_id = uuid.uuid4()
    print(f"Testing with user_id: {user_id} (type: {type(user_id)})")
    
    org = Organization(
        org_id="ORG_001",
        org_name="Test Org",
        manager_user_id=user_id,
        is_current=True,
        sync_version=1
    )
    session.add(org)
    session.commit()
    print("Organization committed successfully.")

    roles = get_business_linked_roles(session, user_id)
    print(f"Roles found: {roles}")
    
    assert "DEPT_MANAGER" in roles
    print("Test passed!")

except Exception as e:
    print(f"Test failed with error: {e}")
    import traceback
    traceback.print_exc()

finally:
    session.close()

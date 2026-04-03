
import uuid
import os
import sys

# Ensure the library can be found
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, User, Organization

# Use SQLite memory DB, which is where the issues happen
DB_URI = "sqlite:///:memory:"
engine = create_engine(DB_URI, connect_args={"check_same_thread": False})

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=engine)

def reproduce():
    # 1. Create tables
    Base.metadata.create_all(engine)
    print("Tables created successfully.")
    
    session = SessionLocal()
    try:
        # 2. Create an organization
        print("Creating an organization...")
        org = Organization(org_code="ORG1", org_name="Test Org")
        session.add(org)
        session.flush()
        print(f"Organization created with ID: {org.id}")
        
        # 3. Create a user in that organization
        print("Creating a user in that organization...")
        uid = uuid.uuid4()
        user = User(
            global_user_id=uid,
            primary_email="test@example.com",
            username="testuser",
            full_name="Test User",
            department_id=org.id
        )
        session.add(user)
        session.flush() # This might trigger the circular dependency if not handled correctly
        print(f"User created with global_user_id: {user.global_user_id}")
        
        # 4. Set the user as the manager of the organization (Circular!)
        print("Setting user as the manager of the organization (Circular!)...")
        org.manager_user_id = uid
        session.flush()
        
        print("Successfully flushed circular dependency!")
        session.commit()
    except Exception as e:
        print(f"FAILED with: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    reproduce()

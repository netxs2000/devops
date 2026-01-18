import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

# Import from auth_database or create SessionLocal using config
from devops_collector.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import IdentityMapping, User

def check_data():
    # Setup simple DB connection directly using config settings
    engine = create_engine(settings.database.uri)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        count = db.query(IdentityMapping).count()
        print(f"Total records in mdm_identity_mappings: {count}")
        
        if count > 0:
            sample = db.query(IdentityMapping).first()
            print(f"Sample - Source: {sample.source_system}, User: {sample.external_username}")
        else:
            print("No records found in mdm_identity_mappings.")

        user_count = db.query(User).count()
        print(f"Total records in mdm_identities (User table): {user_count}")
        if user_count > 0:
            # Try to get a real employee
            sample_user = db.query(User).filter(User.employee_id.isnot(None)).first()
            if sample_user:
                print(f"Sample Employee - Name: {sample_user.full_name}, Email: {sample_user.primary_email}, EmployeeID: {sample_user.employee_id}")
            else:
                sample_user = db.query(User).first()
                print(f"Sample User (System) - Name: {sample_user.full_name}, Email: {sample_user.primary_email}, EmployeeID: {sample_user.employee_id}")
        else:
            print("No records found in mdm_identities.")
            
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_data()

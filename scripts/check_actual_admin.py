
import sys
import os
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models.base_models import User, SysRole, UserRole
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def check_admin():
    engine = create_engine(settings.database.uri)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        user = session.query(User).filter_by(primary_email="admin@tjhq.com", is_current=True).first()
        if not user:
            print("User admin@tjhq.com not found")
            return
        
        print(f"User: {user.full_name} ({user.primary_email})")
        print(f"Roles: {[r.role_key for r in user.roles]}")
        
        # Check permissions in JWT simulated way
        from devops_collector.core import security
        perms = security.get_user_permissions(session, user)
        print(f"Permissions: {perms}")
        
    finally:
        session.close()

if __name__ == "__main__":
    check_admin()

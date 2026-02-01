"""
Seed an E2E test user with SYSTEM_ADMIN role.
"""

import sys
import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from devops_collector.config import settings
from devops_collector.models.base_models import User, UserCredential, SysRole, UserRole
from devops_collector.auth.auth_service import auth_get_password_hash

def seed_e2e_admin():
    engine = create_engine(settings.database.uri)
    with Session(engine) as session:
        email = os.getenv("E2E_TEST_USER_EMAIL", "e2e_test@example.com")
        password = os.getenv("E2E_TEST_USER_PASSWORD", "e2e_test_password")
        
        # Check if user exists
        user = session.query(User).filter_by(primary_email=email).first()
        if not user:
            user = User(
                global_user_id=uuid.uuid4(),
                employee_id="E2E-ADMIN",
                username="e2e_admin",
                full_name="E2E Test Administrator",
                primary_email=email,
                is_active=True,
                is_current=True,
                sync_version=1
            )
            session.add(user)
            session.flush()
            
            cred = UserCredential(
                user_id=user.global_user_id,
                password_hash=auth_get_password_hash(password)
            )
            session.add(cred)
            print(f"Created E2E user: {email}")
        else:
            user.is_active = True
            print(f"E2E user already exists: {email}")

        # Ensure SYSTEM_ADMIN role
        admin_role = session.query(SysRole).filter_by(role_key='SYSTEM_ADMIN').first()
        if not admin_role:
            admin_role = SysRole(
                role_key='SYSTEM_ADMIN',
                role_name='系统管理员',
                is_active=True
            )
            session.add(admin_role)
            session.flush()
            print("Created SYSTEM_ADMIN role")

        # Link role
        link = session.query(UserRole).filter_by(user_id=user.global_user_id, role_id=admin_role.id).first()
        if not link:
            link = UserRole(user_id=user.global_user_id, role_id=admin_role.id)
            session.add(link)
            print("Linked SYSTEM_ADMIN role to E2E user")
        
        session.commit()
        print("Done.")

if __name__ == '__main__':
    seed_e2e_admin()

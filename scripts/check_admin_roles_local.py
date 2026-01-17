
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Set up path to import models
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import User, Role, UserRole, UserCredential

def check_admin():
    # Try localhost instead of 'db' host
    uri = settings.database.uri.replace('@db:', '@127.0.0.1:').replace('@db/', '@127.0.0.1/')
    print(f"Connecting to: {uri}")
    
    try:
        engine = create_engine(uri)
        Session = sessionmaker(bind=engine)
        session = Session()

        admin_email = 'admin@tjhq.com'
        user = session.query(User).filter_by(primary_email=admin_email, is_current=True).first()

        if not user:
            print(f"User {admin_email} not found.")
            # List all users
            print("All users in DB:")
            users = session.query(User).all()
            for u in users:
                print(f" - {u.primary_email} (ID: {u.global_user_id})")
            return

        print(f"User found: {user.full_name}, global_user_id: {user.global_user_id}")
        
        # Fixed query to join Role and UserRole
        roles = session.query(Role).join(UserRole, UserRole.role_id == Role.id).filter(UserRole.user_id == user.global_user_id).all()
        print(f"Roles for {admin_email}:")
        for role in roles:
            print(f" - {role.code} ({role.name})")

        if not roles:
            print("No roles assigned to this user.")
            
        # Check permissions through roles
        for role in roles:
            from devops_collector.models import RolePermission
            rp_list = session.query(RolePermission).filter_by(role_id=role.id).all()
            perms = [p.permission_code for p in rp_list]
            print(f" Permissions for role {role.code}: {perms}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_admin()

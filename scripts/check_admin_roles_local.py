
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Set up path to import models
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import User, SysRole, UserRole, UserCredential, SysMenu

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
        
        # Fixed query to join SysRole and UserRole
        roles = session.query(SysRole).join(UserRole, UserRole.role_id == SysRole.id).filter(UserRole.user_id == user.global_user_id).all()
        print(f"Roles for {admin_email}:")
        for role in roles:
            print(f" - {role.role_key} ({role.role_name})")

        if not roles:
            print("No roles assigned to this user.")
            
        # Check permissions through roles
        for role in roles:
            menus = session.query(SysMenu).join(SysRole.menus).filter(SysRole.id == role.id).all()
            perms = [m.perms for m in menus if m.perms]
            print(f" Permissions for role {role.role_key}: {perms}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_admin()

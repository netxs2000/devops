
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Set up path to import models
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import User, SysRole, UserRole

def check_admin():
    engine = create_engine(settings.database.uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    admin_email = 'admin@tjhq.com'
    user = session.query(User).filter_by(primary_email=admin_email, is_current=True).first()

    if not user:
        print(f"User {admin_email} not found.")
        return

    print(f"User found: {user.full_name}, global_user_id: {user.global_user_id}")
    
    roles = session.query(SysRole).join(UserRole).filter(UserRole.user_id == user.global_user_id).all()
    print(f"Roles for {admin_email}:")
    for role in roles:
        print(f" - {role.role_key} ({role.role_name})")

    if not roles:
        print("No roles assigned to this user.")

if __name__ == "__main__":
    check_admin()

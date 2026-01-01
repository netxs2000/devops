"""初始化 RBAC 权限系统脚本。

该脚本用于：
1. 定义系统级权限点 (Permissions)。
2. 定义默认角色 (Roles)，如 SYSTEM_ADMIN, DEVELOPER。
3. 创建初始超级管理员账号。

使用方法:
    python scripts/init_rbac.py
"""
import sys
import os
import logging
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Ensure devops_collector is in path
sys.path.append(os.getcwd())

from devops_collector.config import Config
from devops_collector.models.base_models import (
    Base, User, Role, Permission, RolePermission, UserCredential, UserRole
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('InitRBAC')

# 密码哈希工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_permissions(session):
    """初始化原子权限点。"""
    permissions = [
        # --- 系统级 ---
        {"code": "SYSTEM:ADMIN", "category": "SYSTEM", "desc": "系统超级管理权限，无视规则"},
        
        # --- 迭代管理 (Agile) ---
        {"code": "ITERATION:VIEW", "category": "ITERATION", "desc": "查看迭代"},
        {"code": "ITERATION:MANAGE", "category": "ITERATION", "desc": "创建/编辑/规划迭代"},
        {"code": "RELEASE:EXECUTE", "category": "ITERATION", "desc": "执行版本发布"},
        
        # --- 用户与组织 (HR) ---
        {"code": "USER:VIEW", "category": "USER", "desc": "查看用户档案"},
        {"code": "USER:MANAGE", "category": "USER", "desc": "管理用户角色与归属"},
        
        # --- 效能洞察 (Analytics) ---
        {"code": "ANALYTICS:VIEW_ALL", "category": "ANALYTICS", "desc": "查看全公司效能报表"},
    ]
    
    logger.info("Initializing Permissions...")
    for p_data in permissions:
        perm = session.query(Permission).filter_by(code=p_data['code']).first()
        if not perm:
            perm = Permission(code=p_data['code'], category=p_data['category'], description=p_data['desc'])
            session.add(perm)
    session.commit()
    return permissions

def init_roles(session):
    """初始化标准角色及其权限映射。"""
    logger.info("Initializing Roles...")
    
    # 1. SYSTEM_ADMIN (超级管理员)
    admin_role = session.query(Role).filter_by(code='SYSTEM_ADMIN').first()
    if not admin_role:
        admin_role = Role(name="系统管理员", code="SYSTEM_ADMIN", description="拥有系统所有权限的超级账号")
        session.add(admin_role)
        session.flush() # get ID
        
        # 赋予所有权限
        all_perms = session.query(Permission).all()
        for p in all_perms:
            rp = RolePermission(role_id=admin_role.id, permission_code=p.code)
            session.add(rp)
            
    # 2. DEVELOPER (普通开发者)
    dev_role = session.query(Role).filter_by(code='DEVELOPER').first()
    if not dev_role:
        dev_role = Role(name="研发工程师", code="DEVELOPER", description="普通研发人员")
        session.add(dev_role)
        session.flush()
        
        # 赋予基础权限
        basic_perms = ["ITERATION:VIEW"]
        for p_code in basic_perms:
            rp = RolePermission(role_id=dev_role.id, permission_code=p_code)
            session.add(rp)
            
    session.commit()

def create_super_admin(session):
    """创建初始超级管理员账户。"""
    admin_email = "admin@devops.local"
    # 默认密码，生产环境请强制修改
    default_password = "admin_password_123!" 
    
    logger.info(f"Checking Super Admin account ({admin_email})...")
    
    user = session.query(User).filter_by(primary_email=admin_email).first()
    if not user:
        logger.info("Creating new Super Admin user...")
        # 1. 创建 User (mdm_identities)
        user = User(
            global_user_id=uuid.uuid4(),
            full_name="Super Admin",
            primary_email=admin_email,
            is_active=True,
            is_survivor=True
        )
        session.add(user)
        session.flush()
        
        # 2. 创建凭证 (Credential)
        pw_hash = pwd_context.hash(default_password)
        cred = UserCredential(
            user_id=user.global_user_id,
            password_hash=pw_hash,
            last_login_at=None
        )
        session.add(cred)
        
        # 3. 绑定 SYSTEM_ADMIN 角色
        admin_role = session.query(Role).filter_by(code='SYSTEM_ADMIN').first()
        if admin_role:
            user_role = UserRole(user_id=user.global_user_id, role_id=admin_role.id)
            session.add(user_role)
        
        session.commit()
        
        logger.info(f"Super Admin created and granted SYSTEM_ADMIN role! Login: {admin_email} / {default_password}")
    else:
        # 确保现有管理员也有角色（补录逻辑）
        admin_role = session.query(Role).filter_by(code='SYSTEM_ADMIN').first()
        if admin_role and admin_role not in user.roles:
            user.roles.append(admin_role)
            session.commit()
            logger.info(f"Role SYSTEM_ADMIN linked to existing user {admin_email}")
        logger.info("Super Admin already exists.")

def main():
    logger.info("Starting RBAC Initialization...")
    
    engine = create_engine(Config.DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. Init Meta
        init_permissions(session)
        init_roles(session)
        
        # 2. Init User
        create_super_admin(session)
        
        logger.info("RBAC Initialization Completed Successfully.")
    except Exception as e:
        session.rollback()
        logger.error(f"Initialization failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()

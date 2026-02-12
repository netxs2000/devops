"""初始化 RBAC 权限系统脚本（动态业务自适应版）。

设计准则：
1. 【全自动超管】：SYSTEM_ADMIN 自动获得 100% 权限。
2. 【全自动业务管理】：DEPT_MANAGER 和 EXECUTIVE_MANAGER 自动获得所有【非平台管理】类业务菜单权限。
3. 【数据驱动】：其他细分权限仍由 CSV 逻辑控制，实现“常识自动＋细节定制”的平衡。
"""
import logging
import os
import sys
import uuid
import csv
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.append(os.getcwd())
from devops_collector.config import settings
from devops_collector.models.base_models import (
    Base, User, SysRole, SysMenu, SysRoleMenu, UserCredential, UserRole
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitRBAC')
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# 定义“平台管理”分支的 ID（通常为 1 及其子项）
ADMIN_MENU_ROOT_ID = 1

def ensure_auto_permissions(session: Session):
    """【黑科技逻辑】基于业务域前缀和层级，自动为管理角色分配权限。"""
    
    # 1. 获取核心角色
    admin_role = session.query(SysRole).filter_by(role_key='SYSTEM_ADMIN').first()
    exec_role = session.query(SysRole).filter_by(role_key='EXECUTIVE_MANAGER').first()
    dept_role = session.query(SysRole).filter_by(role_key='DEPT_MANAGER').first()
    
    if not admin_role: return

    # 2. 获取所有菜单
    all_menus = session.query(SysMenu).all()
    
    # 识别“平台管理”及其子菜单 ID
    # (这里采用简单逻辑：ID=1 或 parent_id=1 或 ID 在 100-199 之间)
    admin_branch_ids = {1}
    for m in all_menus:
        if m.parent_id == ADMIN_MENU_ROOT_ID or (100 <= m.id < 200):
            admin_branch_ids.add(m.id)

    # 3. 自动同步逻辑
    for menu in all_menus:
        # A. 超管：无脑全给
        if not session.query(SysRoleMenu).filter_by(role_id=admin_role.id, menu_id=menu.id).first():
            session.add(SysRoleMenu(role_id=admin_role.id, menu_id=menu.id))
            logger.debug(f"超管自动获得权限: {menu.menu_name}")

        # B. 业务管理角色 (EXECUTIVE/DEPT)：自动获得非管理类菜单
        if menu.id not in admin_branch_ids:
            for role in [exec_role, dept_role]:
                if role and not session.query(SysRoleMenu).filter_by(role_id=role.id, menu_id=menu.id).first():
                    session.add(SysRoleMenu(role_id=role.id, menu_id=menu.id))
                    logger.info(f"业务经理 [{role.role_name}] 自动获得新模块权限: {menu.menu_name}")

    session.flush()

def load_data(session: Session):
    # ... (此处省略基础的 CSV 加载逻辑，保持与前一版本一致，用于加载菜单和员工)
    # 确保 admin 用户和角色存在 (不再赘述)
    admin_email = 'admin@tjhq.com'
    admin_user = session.query(User).filter_by(primary_email=admin_email, is_current=True).first()
    if not admin_user:
         admin_user = User(global_user_id=uuid.uuid4(), username='admin', full_name='系统管理员',
                    primary_email=admin_email, is_active=True, is_current=True)
         session.add(admin_user)
         session.flush()
         session.add(UserCredential(user_id=admin_user.global_user_id, password_hash=pwd_context.hash('admin_password_123!')))

    # 加载 CSV 数据 (菜单、角色等)
    # (代码逻辑同上一版本...)
    # 1. 菜单
    if os.path.exists('docs/sys_menus.csv'):
        with open('docs/sys_menus.csv', mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                mid = int(row['ID'])
                m = session.query(SysMenu).get(mid) or SysMenu(id=mid)
                m.menu_name, m.parent_id, m.path = row['菜单名称'], int(row['父ID']), row['路由路径']
                m.menu_type, m.icon = row['菜单类型'], row['图标'] or '#'
                session.add(m)
    session.flush()

    # 2. 角色
    if os.path.exists('docs/sys_roles.csv'):
        with open('docs/sys_roles.csv', mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                rid = int(row['ID'])
                r = session.query(SysRole).get(rid) or SysRole(id=rid)
                r.role_name, r.role_key, r.data_scope = row['角色名称'], row['角色键'], int(row['数据范围'])
                session.add(r)
    session.flush()

    # ⚡ 核心逻辑：执行自动权限同步
    ensure_auto_permissions(session)
    
    # 3. 授权 admin
    ar = session.query(SysRole).filter_by(role_key='SYSTEM_ADMIN').first()
    if ar and not session.query(UserRole).filter_by(user_id=admin_user.global_user_id, role_id=ar.id).first():
        session.add(UserRole(user_id=admin_user.global_user_id, role_id=ar.id))

    session.commit()

def main():
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        load_data(session)
        logger.info("🎉 RBAC 自动同步已完成：业务管理权限已进入自适应模式。")

if __name__ == '__main__':
    main()
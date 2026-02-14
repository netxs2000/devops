"""初始化 RBAC 权限系统脚本（动态业务自适应版）。

修复点：
1. 修正父 ID 为 0 导致的外键约束错误。
2. 优化权限同步逻辑，避免 SQLAlchemy 循环内查询冲突。
"""
import logging
import os
import sys
import uuid
import csv
from typing import Any
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.append(os.getcwd())
from devops_collector.config import settings
from devops_collector.models.base_models import (
    Base, User, SysRole, SysMenu, SysRoleMenu, UserCredential, UserRole
)
from scripts.utils import build_user_indexes, resolve_user

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitRBAC')
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# 定义“平台管理”分支的 ID（通常为 1 及其子项）
ADMIN_MENU_ROOT_ID = 1

def ensure_auto_permissions(session: Session):
    """【黑科技逻辑】基于业务域前缀和层级，自动为管理角色分配权限。"""
    
    admin_role = session.query(SysRole).filter_by(role_key='SYSTEM_ADMIN').first()
    exec_role = session.query(SysRole).filter_by(role_key='EXECUTIVE_MANAGER').first()
    dept_role = session.query(SysRole).filter_by(role_key='DEPT_MANAGER').first()
    
    if not admin_role: 
        logger.warning("未找到 SYSTEM_ADMIN 角色，跳过自动授权。")
        return

    all_menus = session.query(SysMenu).all()
    
    # 识别“平台管理”分支 ID
    admin_branch_ids = {1}
    for m in all_menus:
        if m.parent_id == ADMIN_MENU_ROOT_ID or (100 <= m.id < 200):
            admin_branch_ids.add(m.id)

    # 预载现有的关系以减少查询
    existing_relations = set(session.query(SysRoleMenu.role_id, SysRoleMenu.menu_id).all())

    to_add = []
    for menu in all_menus:
        # A. 超管：全给
        if (admin_role.id, menu.id) not in existing_relations:
            to_add.append(SysRoleMenu(role_id=admin_role.id, menu_id=menu.id))
            existing_relations.add((admin_role.id, menu.id))

        # B. 业务管理角色：非管理类菜单
        if menu.id not in admin_branch_ids:
            for role in [exec_role, dept_role]:
                if role and (role.id, menu.id) not in existing_relations:
                    to_add.append(SysRoleMenu(role_id=role.id, menu_id=menu.id))
                    existing_relations.add((role.id, menu.id))
                    logger.info(f"业务经理 [{role.role_name}] 获得新模块权限: {menu.menu_name}")

    if to_add:
        session.bulk_save_objects(to_add)
    session.flush()

def load_data(session: Session):
    # 1. 确保 admin 用户存在
    admin_email = 'admin@tjhq.com'
    admin_user = session.query(User).filter_by(primary_email=admin_email, is_current=True).first()
    if not admin_user:
         uid = uuid.uuid4()
         admin_user = User(global_user_id=uid, username='admin', full_name='系统管理员',
                    primary_email=admin_email, is_active=True, is_current=True)
         session.add(admin_user)
         session.flush()
         session.add(UserCredential(user_id=uid, password_hash=pwd_context.hash('admin_password_123!')))
    
    # 2. 加载菜单
    if os.path.exists('docs/sys_menus.csv'):
        with open('docs/sys_menus.csv', mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                mid = int(row['ID'])
                pid = int(row['父ID'])
                # 【关键修复】如果父 ID 为 0，标记为 None (NULL)
                parent_id = pid if pid != 0 else None
                
                m = session.query(SysMenu).get(mid) or SysMenu(id=mid)
                m.menu_name = row['菜单名称']
                m.parent_id = parent_id
                m.path = row['路由路径']
                m.menu_type = row['菜单类型']
                m.icon = row['图标'] or '#'
                m.perms = row.get('权限标识', '')
                session.add(m)
        session.flush()

    # 3. 加载角色
    if os.path.exists('docs/sys_roles.csv'):
        with open('docs/sys_roles.csv', mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                rid = int(row['ID'])
                r = session.query(SysRole).get(rid) or SysRole(id=rid)
                r.role_name, r.role_key, r.data_scope = row['角色名称'], row['角色键'], int(row['数据范围'])
                session.add(r)
        session.flush()

    # 4. 加载角色菜单关联 (sys_role_menus.csv)
    if os.path.exists('docs/sys_role_menus.csv'):
        with open('docs/sys_role_menus.csv', mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                rid, mid = int(row['role_id']), int(row['menu_id'])
                if not session.query(SysRoleMenu).filter_by(role_id=rid, menu_id=mid).first():
                    session.add(SysRoleMenu(role_id=rid, menu_id=mid))
        session.flush()

    # 5. 执行自动权限同步
    ensure_auto_permissions(session)
    
    # 6. 加载用户角色关联 (sys_user_roles.csv) - 支持邮箱和汉字姓名
    if os.path.exists('docs/sys_user_roles.csv'):
        email_idx, name_idx = build_user_indexes(session)
        with open('docs/sys_user_roles.csv', mode='r', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                user_val = row.get('user_id', row.get('邮箱', '')).strip()
                role_id = int(row['role_id'])
                uid = resolve_user(user_val, email_idx, name_idx, '用户角色')
                if uid:
                    if not session.query(UserRole).filter_by(user_id=uid, role_id=role_id).first():
                        session.add(UserRole(user_id=uid, role_id=role_id))
                else:
                    logger.warning(f"用户角色关联跳过: 无法匹配用户 '{user_val}'")
        session.flush()

    # 7. 兜底绑定 admin 角色
    ar = session.query(SysRole).filter_by(role_key='SYSTEM_ADMIN').first()
    if ar and not session.query(UserRole).filter_by(user_id=admin_user.global_user_id, role_id=ar.id).first():
        session.add(UserRole(user_id=admin_user.global_user_id, role_id=ar.id))

    session.commit()

def main():
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        load_data(session)
        logger.info("🎉 RBAC 自动同步已完成：业务自适应模式运行。")

if __name__ == '__main__':
    main()
"""初始化 RBAC 权限系统脚本（内置默认值 + 业务自适应版）。

优化：
1. 内置标准菜单和角色的配置，不再强依赖外部 CSV。
2. 自动根据逻辑分配权限（SYSTEM_ADMIN 获得全部，业务角色获得非管理菜单）。
3. 保持向后兼容：如果存在 docs/sys_*.csv，则以文件内容为准。
"""
import csv
import logging
import sys
import uuid
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models.base_models import (
    Base,
    SysMenu,
    SysRole,
    SysRoleMenu,
    User,
    UserCredential,
    UserRole,
)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitRBAC')
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# --- 默认内置数据定义 (Built-in Defaults) ---

DEFAULT_ROLES = [
    {"id": 1, "name": "系统管理员", "key": "SYSTEM_ADMIN", "scope": 1},
    {"id": 2, "name": "管理层", "key": "EXECUTIVE_MANAGER", "scope": 2},
    {"id": 3, "name": "部门经理", "key": "DEPT_MANAGER", "scope": 3},
    {"id": 4, "name": "项目经理", "key": "PROJECT_MANAGER", "scope": 4},
    {"id": 5, "name": "普通员工", "key": "REGULAR_USER", "scope": 5},
]

DEFAULT_MENUS = [
    {"id": 1, "pid": 0, "name": "平台管理", "path": "/admin", "type": "M", "icon": "setting", "perm": "sys:admin:view"},
    {"id": 101, "pid": 1, "name": "组织架构", "path": "/admin/org", "type": "C", "icon": "tree", "perm": "sys:org:view"},
    {"id": 102, "pid": 1, "name": "用户管理", "path": "/admin/user", "type": "C", "icon": "user", "perm": "sys:user:view"},
    {"id": 103, "pid": 1, "name": "产品定义", "path": "/admin/product", "type": "C", "icon": "shopping-cart", "perm": "sys:product:view"},
    {"id": 104, "pid": 1, "name": "项目主表", "path": "/admin/project", "type": "C", "icon": "project", "perm": "sys:project:view"},

    {"id": 2, "pid": 0, "name": "研发协同", "path": "/devops", "type": "M", "icon": "rocket", "perm": "sys:devops:view"},
    {"id": 201, "pid": 2, "name": "需求池", "path": "/devops/backlog", "type": "C", "icon": "unordered-list", "perm": "pm:backlog:view"},
    {"id": 202, "pid": 2, "name": "迭代看板", "path": "/devops/iteration", "type": "C", "icon": "dashboard", "perm": "pm:iteration:view"},
    {"id": 203, "pid": 2, "name": "质量门禁", "path": "/devops/quality", "type": "C", "icon": "safety-certificate", "perm": "qa:gate:view"},

    {"id": 3, "pid": 0, "name": "测试管理", "path": "/test", "type": "M", "icon": "experiment", "perm": "sys:test:view"},
    {"id": 301, "pid": 3, "name": "测试用例", "path": "/test/cases", "type": "C", "icon": "container", "perm": "qa:test:view"},
    {"id": 302, "pid": 3, "name": "追溯矩阵", "path": "/test/rtm", "type": "C", "icon": "deployment-unit", "perm": "qa:rtm:view"},

    {"id": 4, "pid": 0, "name": "服务支持", "path": "/service", "type": "M", "icon": "customer-service", "perm": "sys:service:view"},
    {"id": 401, "pid": 4, "name": "反馈中心", "path": "/service/desk", "type": "C", "icon": "message", "perm": "sd:ticket:view"},
    {"id": 402, "pid": 4, "name": "知识库", "path": "/service/kb", "type": "C", "icon": "read", "perm": "sd:kb:view"},

    {"id": 5, "pid": 0, "name": "效能看板", "path": "/analytics", "type": "M", "icon": "line-chart", "perm": "sys:analytics:view"},
    {"id": 501, "pid": 5, "name": "DORA指标", "path": "/analytics/dora", "type": "C", "icon": "thunderbolt", "perm": "ana:dora:view"},
    {"id": 502, "pid": 5, "name": "成本分析", "path": "/analytics/cost", "type": "C", "icon": "account-book", "perm": "ana:cost:view"},
]

def ensure_auto_permissions(session: Session):
    """【业务常识授权】超管拥有一切，业务经理拥有非敏感菜单。"""
    admin_role = session.query(SysRole).filter_by(role_key='SYSTEM_ADMIN').first()
    business_roles = session.query(SysRole).filter(SysRole.role_key.in_(['EXECUTIVE_MANAGER', 'DEPT_MANAGER'])).all()

    if not admin_role: return

    all_menus = session.query(SysMenu).all()
    # 平台管理分支的 ID 集合 (ID 为 1 极其子孙)
    admin_branch_ids = {1}
    for m in all_menus:
        if m.parent_id == 1 or (100 <= m.id < 200):
            admin_branch_ids.add(m.id)

    existing = set(session.query(SysRoleMenu.role_id, SysRoleMenu.menu_id).all())
    to_add = []

    for menu in all_menus:
        # 1. 超管必给
        if (admin_role.id, menu.id) not in existing:
            to_add.append(SysRoleMenu(role_id=admin_role.id, menu_id=menu.id))
            existing.add((admin_role.id, menu.id))

        # 2. 业务角色给业务功能菜单
        if menu.id not in admin_branch_ids:
            for br in business_roles:
                if (br.id, menu.id) not in existing:
                    to_add.append(SysRoleMenu(role_id=br.id, menu_id=menu.id))
                    existing.add((br.id, menu.id))

    if to_add:
        session.bulk_save_objects(to_add)
        logger.info(f"已自动分配 {len(to_add)} 项系统权限关联。")

def load_menus(session: Session):
    csv_path = Path('docs/sys_menus.csv')
    if csv_path.exists():
        logger.info("从 CSV 加载菜单配置...")
        with open(csv_path, encoding='utf-8-sig') as f:
            data = list(csv.DictReader(f))
            for row in data:
                mid = int(row['ID'])
                pid = int(row['父ID'])
                m = session.query(SysMenu).get(mid) or SysMenu(id=mid)
                m.menu_name, m.parent_id = row['菜单名称'], (pid if pid != 0 else None)
                m.path, m.menu_type, m.icon = row['路由路径'], row['菜单类型'], row['图标']
                m.perms = row.get('权限标识', '')
                session.add(m)
    else:
        logger.info("使用内置默认菜单配置...")
        for m_def in DEFAULT_MENUS:
            m = session.query(SysMenu).get(m_def['id']) or SysMenu(id=m_def['id'])
            m.menu_name, m.parent_id = m_def['name'], (m_def['pid'] if m_def['pid'] != 0 else None)
            m.path, m.menu_type, m.icon, m.perms = m_def['path'], m_def['type'], m_def['icon'], m_def['perm']
            session.add(m)
    session.flush()

def load_roles(session: Session):
    csv_path = Path('docs/sys_roles.csv')
    if csv_path.exists():
        logger.info("从 CSV 加载角色配置...")
        with open(csv_path, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                rid = int(row['ID'])
                r = session.query(SysRole).get(rid) or SysRole(id=rid)
                r.role_name, r.role_key, r.data_scope = row['角色名称'], row['角色键'], int(row['数据范围'])
                session.add(r)
    else:
        logger.info("使用内置默认角色配置...")
        for r_def in DEFAULT_ROLES:
            r = session.query(SysRole).get(r_def['id']) or SysRole(id=r_def['id'])
            r.role_name, r.role_key, r.data_scope = r_def['name'], r_def['key'], r_def['scope']
            session.add(r)
    session.flush()

def main():
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # 1. 确保 admin 用户
        admin_email = 'admin@tjhq.com'
        admin_user = session.query(User).filter_by(primary_email=admin_email, is_current=True).first()
        if not admin_user:
            uid = uuid.uuid4()
            admin_user = User(global_user_id=uid, username='admin', full_name='系统管理员',
                             primary_email=admin_email, is_active=True, is_current=True)
            session.add(admin_user)
            session.flush()
            session.add(UserCredential(user_id=uid, password_hash=pwd_context.hash('admin_password_123!')))

        # 2. 加载基础数据
        load_menus(session)
        load_roles(session)

        # 3. 自动权限同步 (核心简化：无需 CSV 指定，逻辑自动完成关联)
        ensure_auto_permissions(session)

        # 4. 兜底绑定 admin 角色
        ar = session.query(SysRole).filter_by(role_key='SYSTEM_ADMIN').first()
        if ar and not session.query(UserRole).filter_by(user_id=admin_user.global_user_id, role_id=ar.id).first():
            session.add(UserRole(user_id=admin_user.global_user_id, role_id=ar.id))

        session.commit()
    logger.info("🎉 RBAC 系统初始化/同步完成（内置模式）。")

if __name__ == '__main__':
    main()

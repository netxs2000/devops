"""初始化 RBAC 权限系统脚本 (v2.0)。

本脚本用于自动化初始化 DevOps 平台的权限控制系统，包括：
1. 初始化系统菜单 (SysMenu) - 树形结构，包含目录、菜单、按钮
2. 初始化标准角色 (SysRole) - 支持角色继承和数据范围
3. 建立角色与菜单的关联关系 (SysRoleMenu)
4. 创建初始超级管理员账号

设计决策:
- 角色继承深度: 最多 3 级
- 超管权限: 使用通配符 * 代表所有权限
- 新建角色默认 data_scope: 5 (仅本人)

执行方式:
    python scripts/init_rbac.py
"""

import logging
import os
import sys
import uuid
from typing import List, Dict, Any, Optional

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 添加项目根目录到路径
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models.base_models import (
    Base, User, SysRole, SysMenu, SysRoleMenu, SysRoleDept,
    UserCredential, UserRole
)

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitRBAC')

# 密码加密配置
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# ============================================================================
# 菜单数据定义
# ============================================================================

# 菜单类型常量
MENU_TYPE_DIR = 'M'      # 目录
MENU_TYPE_MENU = 'C'     # 菜单
MENU_TYPE_BUTTON = 'F'   # 按钮

MENU_DATA: List[Dict[str, Any]] = [
    # ========== 一级目录 ==========
    {'id': 1, 'menu_name': '平台管理', 'parent_id': None, 'order_num': 1, 'path': 'admin',
     'menu_type': MENU_TYPE_DIR, 'icon': 'setting', 'perms': '', 'visible': True, 'status': True,
     'remark': 'Administration - 仅管理员可见'},

    {'id': 2, 'menu_name': '支持与战略', 'parent_id': None, 'order_num': 2, 'path': 'strategy',
     'menu_type': MENU_TYPE_DIR, 'icon': 'aim', 'perms': '', 'visible': True, 'status': True,
     'remark': 'Strategy & Support - 所有人可见'},

    {'id': 3, 'menu_name': '洞察与治理', 'parent_id': None, 'order_num': 3, 'path': 'insights',
     'menu_type': MENU_TYPE_DIR, 'icon': 'dashboard', 'perms': '', 'visible': True, 'status': True,
     'remark': 'Governance & Insights - 部门经理+管理员'},

    {'id': 4, 'menu_name': '质量保障', 'parent_id': None, 'order_num': 4, 'path': 'qa',
     'menu_type': MENU_TYPE_DIR, 'icon': 'check-circle', 'perms': '', 'visible': True, 'status': True,
     'remark': 'Quality Assurance - 测试人员+部门经理'},

    {'id': 5, 'menu_name': '项目执行', 'parent_id': None, 'order_num': 5, 'path': 'project',
     'menu_type': MENU_TYPE_DIR, 'icon': 'project', 'perms': '', 'visible': True, 'status': True,
     'remark': 'Project Execution - 开发人员+部门经理'},

    {'id': 6, 'menu_name': '基础服务', 'parent_id': None, 'order_num': 6, 'path': 'foundation',
     'menu_type': MENU_TYPE_DIR, 'icon': 'appstore', 'perms': '', 'visible': True, 'status': True,
     'remark': 'Foundation Services - 所有人'},

    # ========== 平台管理 (1xx) ==========
    {'id': 100, 'menu_name': '用户管理', 'parent_id': 1, 'order_num': 1, 'path': 'users',
     'component': 'admin/users/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'system:user:list',
     'icon': 'user', 'visible': True, 'status': True},

    {'id': 101, 'menu_name': '角色管理', 'parent_id': 1, 'order_num': 2, 'path': 'roles',
     'component': 'admin/roles/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'system:role:list',
     'icon': 'team', 'visible': True, 'status': True},

    {'id': 102, 'menu_name': '菜单管理', 'parent_id': 1, 'order_num': 3, 'path': 'menus',
     'component': 'admin/menus/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'system:menu:list',
     'icon': 'menu', 'visible': True, 'status': True},

    {'id': 103, 'menu_name': '部门管理', 'parent_id': 1, 'order_num': 4, 'path': 'depts',
     'component': 'admin/depts/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'system:dept:list',
     'icon': 'apartment', 'visible': True, 'status': True},

    {'id': 104, 'menu_name': '注册审核', 'parent_id': 1, 'order_num': 5, 'path': 'registrations',
     'component': 'admin/registrations/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'system:registration:list',
     'icon': 'audit', 'visible': True, 'status': True},

    {'id': 105, 'menu_name': '产品系统管理', 'parent_id': 1, 'order_num': 6, 'path': 'products',
     'component': 'admin/products/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'system:product:list',
     'icon': 'product', 'visible': True, 'status': True},

    {'id': 106, 'menu_name': '项目映射配置', 'parent_id': 1, 'order_num': 7, 'path': 'project-mappings',
     'component': 'admin/project-mappings/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'system:project:mapping',
     'icon': 'link', 'visible': True, 'status': True},

    {'id': 107, 'menu_name': '员工身份目录', 'parent_id': 1, 'order_num': 8, 'path': 'employees',
     'component': 'admin/employees/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'system:employee:list',
     'icon': 'contacts', 'visible': True, 'status': True},

    # ========== 支持与战略 (2xx) ==========
    {'id': 200, 'menu_name': 'OKR 目标', 'parent_id': 2, 'order_num': 1, 'path': 'okr',
     'component': 'strategy/okr/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'okr:objective:list',
     'icon': 'flag', 'visible': True, 'status': True},

    {'id': 201, 'menu_name': '路线图', 'parent_id': 2, 'order_num': 2, 'path': 'roadmap',
     'component': 'strategy/roadmap/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'strategy:roadmap:view',
     'icon': 'node-index', 'visible': True, 'status': True},

    {'id': 202, 'menu_name': '服务台', 'parent_id': 2, 'order_num': 3, 'path': 'service-desk',
     'component': 'support/service-desk/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'support:ticket:list',
     'icon': 'customer-service', 'visible': True, 'status': True},

    # ========== 洞察与治理 (3xx) ==========
    {'id': 300, 'menu_name': '效能看板', 'parent_id': 3, 'order_num': 1, 'path': 'dashboard',
     'component': 'insights/dashboard/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'analytics:dashboard:view',
     'icon': 'fund', 'visible': True, 'status': True},

    {'id': 301, 'menu_name': 'DORA 指标', 'parent_id': 3, 'order_num': 2, 'path': 'dora',
     'component': 'insights/dora/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'analytics:dora:view',
     'icon': 'line-chart', 'visible': True, 'status': True},

    {'id': 302, 'menu_name': '成本分析', 'parent_id': 3, 'order_num': 3, 'path': 'costs',
     'component': 'insights/costs/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'finops:cost:view',
     'icon': 'money-collect', 'visible': True, 'status': True},

    {'id': 303, 'menu_name': '合规审计', 'parent_id': 3, 'order_num': 4, 'path': 'compliance',
     'component': 'governance/compliance/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'governance:compliance:view',
     'icon': 'safety', 'visible': True, 'status': True},

    # ========== 质量保障 (4xx) ==========
    {'id': 400, 'menu_name': '需求管理', 'parent_id': 4, 'order_num': 1, 'path': 'requirements',
     'component': 'qa/requirements/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'quality:requirement:list',
     'icon': 'file-text', 'visible': True, 'status': True},

    {'id': 401, 'menu_name': '测试用例', 'parent_id': 4, 'order_num': 2, 'path': 'test-cases',
     'component': 'qa/test-cases/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'quality:testcase:list',
     'icon': 'experiment', 'visible': True, 'status': True},

    {'id': 402, 'menu_name': '测试执行', 'parent_id': 4, 'order_num': 3, 'path': 'executions',
     'component': 'qa/executions/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'quality:execution:list',
     'icon': 'play-circle', 'visible': True, 'status': True},

    {'id': 403, 'menu_name': '缺陷跟踪', 'parent_id': 4, 'order_num': 4, 'path': 'bugs',
     'component': 'qa/bugs/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'quality:bug:list',
     'icon': 'bug', 'visible': True, 'status': True},

    # ========== 项目执行 (5xx) ==========
    {'id': 500, 'menu_name': '迭代计划', 'parent_id': 5, 'order_num': 1, 'path': 'sprints',
     'component': 'project/sprints/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'delivery:sprint:list',
     'icon': 'calendar', 'visible': True, 'status': True},

    {'id': 501, 'menu_name': '任务看板', 'parent_id': 5, 'order_num': 2, 'path': 'kanban',
     'component': 'project/kanban/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'delivery:task:list',
     'icon': 'appstore', 'visible': True, 'status': True},

    {'id': 502, 'menu_name': '代码仓库', 'parent_id': 5, 'order_num': 3, 'path': 'repos',
     'component': 'project/repos/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'delivery:repo:list',
     'icon': 'code', 'visible': True, 'status': True},

    {'id': 503, 'menu_name': '流水线', 'parent_id': 5, 'order_num': 4, 'path': 'pipelines',
     'component': 'project/pipelines/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'delivery:pipeline:list',
     'icon': 'deployment-unit', 'visible': True, 'status': True},

    {'id': 504, 'menu_name': '发布管理', 'parent_id': 5, 'order_num': 5, 'path': 'releases',
     'component': 'project/releases/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'delivery:release:list',
     'icon': 'rocket', 'visible': True, 'status': True},

    # ========== 基础服务 (6xx) ==========
    {'id': 600, 'menu_name': '个人中心', 'parent_id': 6, 'order_num': 1, 'path': 'profile',
     'component': 'foundation/profile/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'user:profile:view',
     'icon': 'user', 'visible': True, 'status': True},

    {'id': 601, 'menu_name': '消息通知', 'parent_id': 6, 'order_num': 2, 'path': 'notifications',
     'component': 'foundation/notifications/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'user:notification:list',
     'icon': 'bell', 'visible': True, 'status': True},

    {'id': 602, 'menu_name': '帮助文档', 'parent_id': 6, 'order_num': 3, 'path': 'help',
     'component': 'foundation/help/index', 'menu_type': MENU_TYPE_MENU, 'perms': 'user:help:view',
     'icon': 'question-circle', 'visible': True, 'status': True},

    # ========== 用户管理按钮权限 (1001-1006) ==========
    {'id': 1001, 'menu_name': '用户查询', 'parent_id': 100, 'order_num': 1,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:user:query'},
    {'id': 1002, 'menu_name': '用户新增', 'parent_id': 100, 'order_num': 2,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:user:add'},
    {'id': 1003, 'menu_name': '用户修改', 'parent_id': 100, 'order_num': 3,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:user:edit'},
    {'id': 1004, 'menu_name': '用户删除', 'parent_id': 100, 'order_num': 4,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:user:delete'},
    {'id': 1005, 'menu_name': '用户导出', 'parent_id': 100, 'order_num': 5,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:user:export'},
    {'id': 1006, 'menu_name': '重置密码', 'parent_id': 100, 'order_num': 6,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:user:resetPwd'},

    # ========== 角色管理按钮权限 (1011-1014) ==========
    {'id': 1011, 'menu_name': '角色查询', 'parent_id': 101, 'order_num': 1,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:role:query'},
    {'id': 1012, 'menu_name': '角色新增', 'parent_id': 101, 'order_num': 2,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:role:add'},
    {'id': 1013, 'menu_name': '角色修改', 'parent_id': 101, 'order_num': 3,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:role:edit'},
    {'id': 1014, 'menu_name': '角色删除', 'parent_id': 101, 'order_num': 4,
     'menu_type': MENU_TYPE_BUTTON, 'perms': 'system:role:delete'},
]

# ============================================================================
# 角色数据定义
# ============================================================================

# 数据范围常量
DATA_SCOPE_ALL = 1           # 全部数据权限
DATA_SCOPE_CUSTOM = 2        # 自定义数据权限
DATA_SCOPE_DEPT = 3          # 本部门数据权限
DATA_SCOPE_DEPT_BELOW = 4    # 本部门及以下数据权限
DATA_SCOPE_SELF = 5          # 仅本人数据权限

ROLE_DATA: List[Dict[str, Any]] = [
    {
        'id': 1,
        'role_name': '超级管理员',
        'role_key': 'SYSTEM_ADMIN',
        'role_sort': 1,
        'data_scope': DATA_SCOPE_ALL,
        'parent_id': 0,
        'remark': '拥有系统所有权限的超级账号，权限标识为 *',
        # 特殊处理：分配所有菜单
        'menu_ids': '*'
    },
    {
        'id': 2,
        'role_name': '部门经理',
        'role_key': 'DEPT_MANAGER',
        'role_sort': 2,
        'data_scope': DATA_SCOPE_DEPT_BELOW,
        'parent_id': 0,
        'remark': '部门负责人，可查看本部门及下级所有数据',
        'menu_ids': [2, 3, 4, 5, 6, 200, 201, 202, 300, 301, 302, 303, 400, 401, 402, 403, 500, 501, 502, 503, 504, 600, 601, 602]
    },
    {
        'id': 3,
        'role_name': '研发工程师',
        'role_key': 'DEVELOPER',
        'role_sort': 3,
        'data_scope': DATA_SCOPE_DEPT_BELOW,
        'parent_id': 0,
        'remark': '日常开发人员，关注项目执行与交付',
        'menu_ids': [2, 5, 6, 200, 201, 202, 500, 501, 502, 503, 504, 600, 601, 602]
    },
    {
        'id': 4,
        'role_name': '测试工程师',
        'role_key': 'QA_ENGINEER',
        'role_sort': 4,
        'data_scope': DATA_SCOPE_DEPT_BELOW,
        'parent_id': 3,  # 继承自研发工程师
        'remark': '负责质量保障，关注测试执行与缺陷跟踪',
        'menu_ids': [2, 4, 6, 200, 201, 202, 400, 401, 402, 403, 600, 601, 602]
    },
    {
        'id': 5,
        'role_name': '交付工程师',
        'role_key': 'DELIVERY_ENGINEER',
        'role_sort': 5,
        'data_scope': DATA_SCOPE_DEPT_BELOW,
        'parent_id': 3,  # 继承自研发工程师
        'remark': '负责项目交付与发布，关注流水线与上线稳定性',
        'menu_ids': [2, 5, 6, 200, 201, 202, 500, 501, 502, 503, 504, 600, 601, 602]
    },
    {
        'id': 6,
        'role_name': '产品经理',
        'role_key': 'PRODUCT_MANAGER',
        'role_sort': 6,
        'data_scope': DATA_SCOPE_DEPT_BELOW,
        'parent_id': 0,
        'remark': '负责规划交付节奏，对产品定义与业务价值目标负责',
        'menu_ids': [2, 3, 4, 5, 6, 200, 201, 202, 300, 301, 400, 401, 402, 403, 500, 501, 502, 503, 504, 600, 601, 602]
    },
    {
        'id': 7,
        'role_name': '财务主管',
        'role_key': 'FINANCE_OFFICER',
        'role_sort': 7,
        'data_scope': DATA_SCOPE_ALL,
        'parent_id': 0,
        'remark': '关注研发投入成本、合同回款与财务合规',
        'menu_ids': [2, 3, 6, 200, 201, 202, 300, 301, 302, 600, 601, 602]
    },
    {
        'id': 8,
        'role_name': '管理层',
        'role_key': 'EXECUTIVE_MANAGER',
        'role_sort': 8,
        'data_scope': DATA_SCOPE_ALL,
        'parent_id': 0,
        'remark': '关注全公司效能、经营目标对齐及成本利润率',
        'menu_ids': [2, 3, 6, 200, 201, 202, 300, 301, 302, 303, 600, 601, 602]
    },
    {
        'id': 9,
        'role_name': '访客',
        'role_key': 'VIEWER',
        'role_sort': 99,
        'data_scope': DATA_SCOPE_SELF,
        'parent_id': 0,
        'remark': '只读权限，仅能查看基础服务',
        'menu_ids': [2, 6, 200, 201, 202, 600, 601, 602]
    },
]


def init_menus(session: Session) -> None:
    """初始化系统菜单结构。

    Args:
        session: SQLAlchemy 数据库会话。
    """
    logger.info('正在初始化系统菜单...')

    for m_data in MENU_DATA:
        menu = session.query(SysMenu).filter_by(id=m_data['id']).first()
        if not menu:
            menu = SysMenu(
                id=m_data['id'],
                menu_name=m_data['menu_name'],
                parent_id=m_data.get('parent_id', 0),
                order_num=m_data.get('order_num', 0),
                path=m_data.get('path', ''),
                component=m_data.get('component'),
                query=m_data.get('query'),
                is_frame=m_data.get('is_frame', False),
                is_cache=m_data.get('is_cache', True),
                menu_type=m_data.get('menu_type', MENU_TYPE_MENU),
                visible=m_data.get('visible', True),
                status=m_data.get('status', True),
                perms=m_data.get('perms', ''),
                icon=m_data.get('icon', '#'),
                remark=m_data.get('remark', '')
            )
            session.add(menu)
        else:
            # 更新已存在的菜单
            menu.menu_name = m_data['menu_name']
            menu.parent_id = m_data.get('parent_id', 0)
            menu.order_num = m_data.get('order_num', 0)
            menu.path = m_data.get('path', '')
            menu.component = m_data.get('component')
            menu.menu_type = m_data.get('menu_type', MENU_TYPE_MENU)
            menu.perms = m_data.get('perms', '')
            menu.icon = m_data.get('icon', '#')
            menu.remark = m_data.get('remark', '')

    session.commit()
    logger.info(f'已初始化 {len(MENU_DATA)} 个菜单项')


def init_roles(session: Session) -> None:
    """初始化标准角色及其菜单权限映射。

    Args:
        session: SQLAlchemy 数据库会话。
    """
    logger.info('正在初始化标准角色...')

    # 获取所有菜单 ID (用于超管)
    all_menu_ids = [m['id'] for m in MENU_DATA]

    for r_data in ROLE_DATA:
        role = session.query(SysRole).filter_by(id=r_data['id']).first()
        if not role:
            role = SysRole(
                id=r_data['id'],
                role_name=r_data['role_name'],
                role_key=r_data['role_key'],
                role_sort=r_data['role_sort'],
                data_scope=r_data['data_scope'],
                parent_id=r_data['parent_id'],
                status=True,
                del_flag=False,
                remark=r_data['remark']
            )
            session.add(role)
            session.flush()
        else:
            # 更新已存在的角色
            role.role_name = r_data['role_name']
            role.role_sort = r_data['role_sort']
            role.data_scope = r_data['data_scope']
            role.parent_id = r_data['parent_id']
            role.remark = r_data['remark']

        # 清理旧的角色-菜单关联
        session.query(SysRoleMenu).filter_by(role_id=role.id).delete()

        # 确定要分配的菜单
        menu_ids = r_data['menu_ids']
        if menu_ids == '*':
            menu_ids = all_menu_ids

        # 创建新的角色-菜单关联
        for menu_id in menu_ids:
            role_menu = SysRoleMenu(role_id=role.id, menu_id=menu_id)
            session.add(role_menu)

    session.commit()
    logger.info(f'已初始化 {len(ROLE_DATA)} 个角色')


def create_super_admin(session: Session) -> None:
    """创建或更新初始超级管理员账户。

    Args:
        session: SQLAlchemy 数据库会话。
    """
    admin_email = 'admin@tjhq.com'
    default_password = 'admin_password_123!'

    logger.info(f'正在检查超级管理员账号 ({admin_email})...')
    user = session.query(User).filter_by(primary_email=admin_email, is_current=True).first()

    if not user:
        logger.info('正在创建新的超级管理员用户...')
        user = User(
            global_user_id=uuid.uuid4(),
            username='admin',
            full_name='系统管理员',
            primary_email=admin_email,
            is_active=True,
            is_survivor=True,
            sync_version=1,
            is_current=True,
            is_deleted=False
        )
        session.add(user)
        session.flush()

        pw_hash = pwd_context.hash(default_password)
        cred = UserCredential(user_id=user.global_user_id, password_hash=pw_hash)
        session.add(cred)

    # 确保关联到超级管理员角色 (新版 SysRole)
    admin_role = session.query(SysRole).filter_by(role_key='SYSTEM_ADMIN').first()
    if admin_role:
        existing_ur = session.query(UserRole).filter_by(
            user_id=user.global_user_id, role_id=admin_role.id
        ).first()
        if not existing_ur:
            user_role = UserRole(user_id=user.global_user_id, role_id=admin_role.id)
            session.add(user_role)

    session.commit()
    logger.info(f'超级管理员账号已就绪。登录邮箱: {admin_email}, 初始密码: {default_password}')


def validate_role_hierarchy(session: Session) -> bool:
    """验证角色继承层级不超过 3 级。

    Args:
        session: SQLAlchemy 数据库会话。

    Returns:
        bool: 验证是否通过。
    """
    logger.info('正在验证角色继承层级...')

    def get_hierarchy_depth(role_id: int, depth: int = 1) -> int:
        """递归计算角色继承深度。"""
        if depth > 3:
            return depth
        role = session.query(SysRole).filter_by(id=role_id).first()
        if not role or role.parent_id == 0:
            return depth
        return get_hierarchy_depth(role.parent_id, depth + 1)

    all_roles = session.query(SysRole).all()
    for role in all_roles:
        depth = get_hierarchy_depth(role.id)
        if depth > 3:
            logger.error(f'角色 {role.role_name} (ID={role.id}) 继承层级 {depth} 超过限制 (最大 3 级)')
            return False
        logger.debug(f'角色 {role.role_name} 继承层级: {depth}')

    logger.info('角色继承层级验证通过')
    return True


def main():
    """RBAC 初始化脚本主入口。"""
    logger.info('=' * 60)
    logger.info('开始执行 RBAC 2.0 初始化流程...')
    logger.info('=' * 60)

    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Step 1: 初始化菜单
        init_menus(session)

        # Step 2: 初始化角色
        init_roles(session)

        # Step 3: 验证角色继承层级
        if not validate_role_hierarchy(session):
            raise ValueError('角色继承层级验证失败')

        # Step 4: 创建超级管理员
        create_super_admin(session)

        logger.info('=' * 60)
        logger.info('RBAC 2.0 初始化已成功完成!')
        logger.info('=' * 60)

    except Exception as e:
        session.rollback()
        logger.error(f'RBAC 脚本执行失败: {e}')
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
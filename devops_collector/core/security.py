"""DevOps Collector Security Core - RBAC 2.0

实现统一的 RBAC 权限校验和行级数据权限 (Row-Level Security) 过滤。

数据范围 (data_scope) 定义:
- 1: 全部数据权限
- 2: 自定义数据权限 (通过 sys_role_dept 指定)
- 3: 本部门数据权限
- 4: 本部门及以下数据权限
- 5: 仅本人数据权限

设计决策:
- 角色继承深度: 最多 3 级
- 超管权限: 使用通配符 * 代表所有权限
- 多角色取并集: 用户拥有多角色时，取所有角色权限的并集
- 数据范围取最大: 多角色时，取数值最小的 data_scope (权限最大)
"""
import logging
from typing import List, Any, Set, Optional
from sqlalchemy.orm import Session, Query
from devops_collector.models.base_models import (
    Organization, User, Product, SysRole, SysRoleDept, SysRoleMenu, SysMenu
)

logger = logging.getLogger(__name__)

# 数据范围常量
DATA_SCOPE_ALL = 1            # 全部数据权限
DATA_SCOPE_CUSTOM = 2         # 自定义数据权限
DATA_SCOPE_DEPT = 3           # 本部门数据权限
DATA_SCOPE_DEPT_BELOW = 4     # 本部门及以下数据权限
DATA_SCOPE_SELF = 5           # 仅本人数据权限

# 超管权限通配符
ADMIN_PERMISSION_WILDCARD = '*'
ADMIN_ROLE_KEY = 'SYSTEM_ADMIN'

# 角色继承最大深度
MAX_ROLE_HIERARCHY_DEPTH = 3


def generate_random_password(length: int = 16) -> str:
    """生成安全的随机密码。
    
    用于 OAuth 自动创建账户时分配初始占位密码。
    """
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def get_user_org_scope_ids(db: Session, user: User) -> List[str]:
    """获取用户组织权限范围内的所有部门 ID (支持无限级向下递归)。

    Args:
        db: SQLAlchemy 数据库会话
        user: 带有 department_id 的用户对象

    Returns:
        List[str]: 所有授权范围内的组织 ID 列表
    """
    user_dept_id = getattr(user, 'department_id', None)
    if not user_dept_id:
        return []
    scope_ids = [user_dept_id]

    def collect_children_orgs(parent_id: str, db_session: Session) -> None:
        """递归收集所有子级组织的 ID。

        Args:
            parent_id: 父级组织 ID。
            db_session: 数据库会话。
        """
        children = db_session.query(Organization.org_id).filter(
            Organization.parent_org_id == parent_id,
            Organization.is_current == True
        ).all()
        for child_row in children:
            child_id = child_row[0]
            scope_ids.append(child_id)
            collect_children_orgs(child_id, db_session)

    collect_children_orgs(user_dept_id, db)
    return list(set(scope_ids))


def get_role_hierarchy(db: Session, role: SysRole, depth: int = 1) -> List[SysRole]:
    """获取角色继承链 (包含父角色)。

    Args:
        db: 数据库会话
        role: 当前角色
        depth: 当前递归深度

    Returns:
        角色继承链列表 (从当前角色到顶层父角色)
    """
    if depth > MAX_ROLE_HIERARCHY_DEPTH:
        logger.warning(f'角色 {role.role_name} 继承深度超过 {MAX_ROLE_HIERARCHY_DEPTH} 级，截断处理')
        return [role]

    chain = [role]
    if role.parent_id and role.parent_id != 0:
        parent_role = db.query(SysRole).filter_by(id=role.parent_id, del_flag=False).first()
        if parent_role:
            chain.extend(get_role_hierarchy(db, parent_role, depth + 1))

    return chain


def get_user_effective_data_scope(db: Session, user: User) -> int:
    """获取用户有效的数据范围 (多角色取权限最大者)。

    Args:
        db: 数据库会话
        user: 用户对象

    Returns:
        int: 有效的 data_scope 值 (1-5，数值越小权限越大)
    """
    if not hasattr(user, 'roles') or not user.roles:
        return DATA_SCOPE_SELF  # 默认仅本人

    min_scope = DATA_SCOPE_SELF
    for role in user.roles:
        # 考虑角色继承
        role_chain = get_role_hierarchy(db, role)
        for r in role_chain:
            if r.data_scope and r.data_scope < min_scope:
                min_scope = r.data_scope

    return min_scope


def get_custom_dept_ids(db: Session, user: User) -> List[str]:
    """获取用户自定义数据权限范围内的部门 ID 列表。

    通过 sys_role_dept 表获取所有角色关联的自定义部门。

    Args:
        db: 数据库会话
        user: 用户对象

    Returns:
        List[str]: 自定义授权的部门 ID 列表
    """
    if not hasattr(user, 'roles') or not user.roles:
        return []

    dept_ids: Set[str] = set()
    for role in user.roles:
        role_chain = get_role_hierarchy(db, role)
        for r in role_chain:
            custom_depts = db.query(SysRoleDept.dept_id).filter_by(role_id=r.id).all()
            dept_ids.update([d[0] for d in custom_depts])

    return list(dept_ids)


def get_user_permissions(db: Session, user: User) -> List[str]:
    """聚合用户所有角色的权限标识 (考虑继承)。

    Args:
        db: 数据库会话
        user: 用户对象

    Returns:
        List[str]: 权限标识列表
    """
    if not hasattr(user, 'roles') or not user.roles:
        return []

    permissions: Set[str] = set()
    for role in user.roles:
        # 超管直接返回通配符
        if role.role_key == ADMIN_ROLE_KEY:
            return [ADMIN_PERMISSION_WILDCARD]

        # 获取角色继承链
        role_chain = get_role_hierarchy(db, role)
        for r in role_chain:
            # 获取角色关联的菜单权限
            role_menus = db.query(SysMenu.perms).join(
                SysRoleMenu, SysRoleMenu.menu_id == SysMenu.id
            ).filter(
                SysRoleMenu.role_id == r.id,
                SysMenu.perms != None,
                SysMenu.perms != '',
                SysMenu.status == True
            ).all()

            for menu in role_menus:
                if menu[0]:
                    permissions.add(menu[0])

    return list(permissions)


def has_permission(db: Session, user: User, required_perm: str) -> bool:
    """检查用户是否拥有指定权限。

    Args:
        db: 数据库会话
        user: 用户对象
        required_perm: 要求的权限标识

    Returns:
        bool: 是否拥有权限
    """
    user_perms = get_user_permissions(db, user)

    # 超管通配符
    if ADMIN_PERMISSION_WILDCARD in user_perms:
        return True

    return required_perm in user_perms


def is_admin(user: User) -> bool:
    """检查用户是否为超级管理员。

    Args:
        user: 用户对象

    Returns:
        bool: 是否为超管
    """
    if not hasattr(user, 'roles') or not user.roles:
        return False

    return any(r.role_key == ADMIN_ROLE_KEY for r in user.roles)


def apply_row_level_security(
    db: Session,
    query: Query,
    model_class: Any,
    current_user: User,
    dept_field: str = 'dept_id',
    owner_field: str = 'create_by'
) -> Query:
    """行级数据权限过滤器 (RLS)。

    根据用户角色的 data_scope 配置，自动过滤数据行。

    Args:
        db: 数据库会话
        query: SQLAlchemy 查询对象
        model_class: 模型类
        current_user: 当前用户
        dept_field: 部门字段名 (默认 dept_id)
        owner_field: (已废弃) 请即使重写 OwnableMixin.get_owner_column
    
    Returns:
        Query: 过滤后的查询对象
    """
    # 超管跳过过滤
    if is_admin(current_user):
        return query

    data_scope = get_user_effective_data_scope(db, current_user)

    if data_scope == DATA_SCOPE_ALL:
        return query

    if data_scope == DATA_SCOPE_CUSTOM:
        allowed_dept_ids = get_custom_dept_ids(db, current_user)
        if hasattr(model_class, dept_field):
            return query.filter(getattr(model_class, dept_field).in_(allowed_dept_ids))
        return query

    if data_scope == DATA_SCOPE_DEPT:
        user_dept_id = getattr(current_user, 'department_id', None)
        if user_dept_id and hasattr(model_class, dept_field):
            return query.filter(getattr(model_class, dept_field) == user_dept_id)
        return query

    if data_scope == DATA_SCOPE_DEPT_BELOW:
        scope_ids = get_user_org_scope_ids(db, current_user)
        if hasattr(model_class, dept_field):
            return query.filter(getattr(model_class, dept_field).in_(scope_ids))
        return query

    if data_scope == DATA_SCOPE_SELF:
        user_id = getattr(current_user, 'global_user_id', None)
        owner_col = None
        
        # 1. 优先使用 OwnableMixin 接口
        if hasattr(model_class, 'get_owner_column'):
            owner_col = model_class.get_owner_column()
            
        # 2. 回退到参数指定 (兼容)
        if owner_col is None and hasattr(model_class, owner_field):
             owner_col = getattr(model_class, owner_field)

        if user_id and owner_col is not None:
            return query.filter(owner_col == user_id)
        
        # [Security] Fail-closed
        from sqlalchemy import false
        return query.filter(false())

    return query


def apply_plugin_privacy_filter(
    db: Session,
    query: Query,
    model_class: Any,
    current_user: User
) -> Query:
    """通用的插件数据隔离过滤器 (兼容旧版 API)。

    自动根据模型中存在的关联字段应用组织树递归隔离。

    Args:
        db: 数据库会话
        query: SQLAlchemy 查询对象
        model_class: 模型类
        current_user: 当前用户

    Returns:
        Query: 过滤后的查询对象
    """
    # 超管跳过过滤
    if is_admin(current_user):
        return query

    # 优先使用新版 RLS
    scope_ids = get_user_org_scope_ids(db, current_user)

    if hasattr(model_class, 'organization_id'):
        return query.filter(model_class.organization_id.in_(scope_ids))

    if hasattr(model_class, 'org_id'):
        return query.filter(model_class.org_id.in_(scope_ids))

    if hasattr(model_class, 'dept_id'):
        return query.filter(model_class.dept_id.in_(scope_ids))

    if hasattr(model_class, 'product_id'):
        return query.join(Product).filter(Product.owner_team_id.in_(scope_ids))

    if hasattr(model_class, 'gitlab_project_id'):
        from devops_collector.plugins.gitlab.models import GitLabProject
        return query.join(GitLabProject).filter(GitLabProject.organization_id.in_(scope_ids))

    if model_class == User:
        return query.filter(User.department_id.in_(scope_ids), User.is_current == True)

    if model_class == Organization:
        return query.filter(Organization.org_id.in_(scope_ids), Organization.is_current == True)

    return query


def get_user_data_scope_ids(user: User) -> List[str]:
    """[P4] 获取用户数据权限范围内的所有地点 ID (含子级)。"""
    user_location = getattr(user, 'location', None)
    if not user_location:
        return []
    scope_ids = [user_location.location_id]

    def collect_children(loc) -> None:
        """递归收集所有子级地点的 ID。

        Args:
            loc: 当前地点对象。
        """
        for child in loc.children:
            scope_ids.append(child.location_id)
            collect_children(child)

    collect_children(user_location)
    return scope_ids


def filter_issues_by_province(
    db: Session,
    issues: List[dict],
    current_user: User
) -> List[dict]:
    """[P4 升级版] 基于 MDM Location 树进行数据权限隔离。

    - 全国权限 (Global): user.location 为空 -> 返回全量
    - 级联权限 (Regional): 返回用户所属地点及其所有下级地点的数据
    """
    user_location = getattr(current_user, 'location', None)
    if not user_location:
        return issues

    scope_loc_ids = get_user_data_scope_ids(current_user)
    from devops_collector.models.base_models import Location
    scope_short_names = [
        loc.short_name for loc in
        db.query(Location.short_name).filter(Location.location_id.in_(scope_loc_ids)).all()
    ]

    filtered = []
    for issue in issues:
        labels = issue.get('labels', [])
        province_tag = 'nationwide'
        for label in labels:
            if label.startswith('province::'):
                province_tag = label.split('::')[1]
                break
        if province_tag in scope_short_names:
            filtered.append(issue)

    return filtered


def filter_issues_by_privacy(
    db: Session,
    issues: List[dict],
    current_user: User
) -> List[dict]:
    """综合维度数据权限隔离（地域 + 组织）。

    依据登录用户的 MDM 属性应用双重过滤机制：
    1. 地域过滤：基于地理位置树进行级联控制 (Region Tree)。
    2. 组织过滤：基于部门 ID 进行无限级向下递归控制 (Dept Tree)。
    """
    filtered_by_loc = filter_issues_by_province(db, issues, current_user)

    user_dept_id = getattr(current_user, 'department_id', None)
    if not user_dept_id:
        return filtered_by_loc

    scope_org_ids = get_user_org_scope_ids(db, current_user)

    final_filtered = []
    for issue in filtered_by_loc:
        labels = issue.get('labels', [])
        dept_tag = None
        for label in labels:
            if label.startswith('dept::'):
                dept_tag = label.split('::')[1]
                break
        if not dept_tag or dept_tag in scope_org_ids:
            final_filtered.append(issue)

    return final_filtered
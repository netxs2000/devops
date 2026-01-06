"""
DevOps Collector Security Core
Implementation of unified RBAC and Privacy Filtering (P5).
"""
import logging
from typing import List, Any, Optional
from sqlalchemy.orm import Session, Query
from devops_collector.models.base_models import Organization, User, Product
logger = logging.getLogger(__name__)

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

    def collect_children_orgs(parent_id, db_session):
        '''"""TODO: Add description.

Args:
    parent_id: TODO
    db_session: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        children = db_session.query(Organization.org_id).filter(Organization.parent_org_id == parent_id, Organization.is_current == True).all()
        for child_row in children:
            child_id = child_row[0]
            scope_ids.append(child_id)
            collect_children_orgs(child_id, db_session)
    collect_children_orgs(user_dept_id, db)
    return list(set(scope_ids))

def apply_plugin_privacy_filter(db: Session, query: Query, model_class: Any, current_user: User) -> Query:
    """通用的插件数据隔离过滤器 (P5)。
    
    自动根据模型中存在的关联字段（organization_id, product_id, gitlab_project_id）应用组织树递归隔离。
    """
    if current_user.role == 'admin':
        return query
    scope_ids = get_user_org_scope_ids(db, current_user)
    if hasattr(model_class, 'organization_id'):
        return query.filter(model_class.organization_id.in_(scope_ids))
    if hasattr(model_class, 'product_id'):
        return query.join(Product).filter(Product.organization_id.in_(scope_ids))
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

    def collect_children(loc):
        '''"""TODO: Add description.

Args:
    loc: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        for child in loc.children:
            scope_ids.append(child.location_id)
            collect_children(child)
    collect_children(user_location)
    return scope_ids

def filter_issues_by_province(db: Session, issues: List[dict], current_user: User) -> List[dict]:
    """[P4 升级版] 基于 MDM Location 树进行数据权限隔离。
    
    - 全国权限 (Global): user.location 为空 -> 返回全量
    - 级联权限 (Regional): 返回用户所属地点及其所有下级地点的数据
    """
    user_location = getattr(current_user, 'location', None)
    if not user_location:
        return issues
    scope_loc_ids = get_user_data_scope_ids(current_user)
    from devops_collector.models.base_models import Location
    scope_short_names = [loc.short_name for loc in db.query(Location.short_name).filter(Location.location_id.in_(scope_loc_ids)).all()]
    filtered = []
    for issue in issues:
        labels = issue.get('labels', [])
        province_tag = 'nationwide'
        for l in labels:
            if l.startswith('province::'):
                province_tag = l.split('::')[1]
                break
        if province_tag in scope_short_names:
            filtered.append(issue)
    return filtered

def filter_issues_by_privacy(db: Session, issues: List[dict], current_user: User) -> List[dict]:
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
        for l in labels:
            if l.startswith('dept::'):
                dept_tag = l.split('::')[1]
                break
        if not dept_tag or dept_tag in scope_org_ids:
            final_filtered.append(issue)
    return final_filtered
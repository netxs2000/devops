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
        children = db_session.query(Organization.org_id).filter(Organization.parent_org_id == parent_id).all()
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
    
    # 1. 直接关联 organization_id (如 Project, Organization)
    if hasattr(model_class, 'organization_id'):
        return query.filter(model_class.organization_id.in_(scope_ids))
        
    # 2. 关联 Product (如 JFrogArtifact, NexusComponent)
    if hasattr(model_class, 'product_id'):
        return query.join(Product).filter(Product.organization_id.in_(scope_ids))

    # 3. 关联 GitLab Project (如 JenkinsJob)
    if hasattr(model_class, 'gitlab_project_id'):
        from devops_collector.plugins.gitlab.models import Project
        return query.join(Project).filter(Project.organization_id.in_(scope_ids))
        
    # 4. 特殊处理用户模型（仅能看到自己部门的人）
    if model_class == User:
        return query.filter(User.department_id.in_(scope_ids))

    return query

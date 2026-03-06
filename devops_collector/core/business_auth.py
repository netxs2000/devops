"""业务关联授权核心逻辑 (Business-Linked Authorization).

依据业务实体（如部门、产品、项目）的所有权或管理权，动态生成用户权限。
此模块补充了传统 RBAC 2.0 的不足，实现了“身份随事走”。
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from devops_collector.models.base_models import (
    Organization,
    Product,
    ProjectMaster,
    SysMenu,
    SysRole,
    SysRoleMenu,
    Team,
)
from devops_collector.plugins.gitlab.models import GitLabGroupMember, GitLabProjectMember


logger = logging.getLogger(__name__)

# 定义业务映射关系
BUSINESS_ROLE_MAP = {
    "org_manager": "DEPT_MANAGER",
    "dept_manager": "DEPT_MANAGER",  # 新增映射
    "product_manager": "PRODUCT_MANAGER",
    "project_manager": "PROJECT_MANAGER",
}


def get_business_linked_roles(db: Session, user_id: Any) -> list[str]:
    """查询用户因业务关联而动态获得的虚拟角色。"""
    roles = []

    # 1. 检查是否为部门负责人
    managed_orgs = db.query(Organization.org_id).filter_by(manager_user_id=user_id, is_current=True).all()
    if managed_orgs:
        roles.append(BUSINESS_ROLE_MAP["org_manager"])

    # 2. 检查是否为产品负责人
    managed_prods = (
        db.query(Product.product_id)
        .filter(
            (Product.product_manager_id == user_id) | (Product.dev_lead_id == user_id) | (Product.qa_lead_id == user_id),
            Product.is_current,
        )
        .all()
    )
    if managed_prods:
        roles.append(BUSINESS_ROLE_MAP["product_manager"])

    # 3. 检查是否为项目负责人
    managed_projects = (
        db.query(ProjectMaster.project_id)
        .filter(
            (ProjectMaster.pm_user_id == user_id) | (ProjectMaster.dev_lead_id == user_id),
            ProjectMaster.is_current,
        )
        .all()
    )
    if managed_projects:
        roles.append(BUSINESS_ROLE_MAP["project_manager"])

    # 4. 检查是否为虚拟团队负责人
    managed_teams = db.query(Team.id).filter_by(leader_id=user_id, is_current=True).all()
    if managed_teams:
        roles.append(BUSINESS_ROLE_MAP["dept_manager"])  # 团队负责人暂按部门经理权限映射

    # 5. 检查 GitLab 权限 (Maintainer=40, Owner=50)
    # GitLab 群组负责人映射为部门经理
    managed_gitlab_groups = db.query(GitLabGroupMember.id).filter(GitLabGroupMember.user_id == user_id, GitLabGroupMember.access_level >= 40).all()
    if managed_gitlab_groups:
        roles.append(BUSINESS_ROLE_MAP["org_manager"])

    # GitLab 项目负责人映射为项目经理
    managed_gitlab_projects = db.query(GitLabProjectMember.id).filter(GitLabProjectMember.user_id == user_id, GitLabProjectMember.access_level >= 40).all()
    if managed_gitlab_projects:
        roles.append(BUSINESS_ROLE_MAP["project_manager"])

    return list(set(roles))


def get_dynamic_permissions(db: Session, user_id: Any) -> set[str]:
    """根据业务关联，动态计算用户应当获得的权限标识并集。"""
    dynamic_roles = get_business_linked_roles(db, user_id)
    if not dynamic_roles:
        return set()

    # 获取这些虚拟角色对应的所有权限标识
    permissions = (
        db.query(SysMenu.perms)
        .join(SysRoleMenu, SysRoleMenu.menu_id == SysMenu.id)
        .join(SysRole, SysRole.id == SysRoleMenu.role_id)
        .filter(SysRole.role_key.in_(dynamic_roles), SysMenu.perms is not None, SysMenu.perms != "", SysMenu.status)
        .all()
    )

    return {p[0] for p in permissions if p[0]}

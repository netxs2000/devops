"""DevOps Portal - Shared Dependencies and Utility Functions for API Routers.

提供统一的认证、授权和数据权限依赖注入。

RBAC 2.0 特性:
- RoleRequired: 基于角色的访问控制
- PermissionRequired: 基于权限标识的访问控制
- DataScopeFilter: 行级数据权限过滤
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from devops_collector.auth import auth_service
from devops_collector.core import security
from devops_collector.auth.auth_database import AuthSessionLocal, get_auth_db
from devops_collector.models.base_models import Location, User

from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger(__name__)

# 定义一个不强制报错的 OAuth2 方案，用于同时支持 Header 和 Query Token
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login', auto_error=False)


async def get_current_user(
    token: Optional[str] = Query(None),
    auth_header: Optional[str] = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_auth_db)
) -> User:
    """获取并校验当前已登录用户。

    支持通过请求头 (Authorization) 或 URL 查询参数 (token) 进行身份检查。

    Args:
        token: URL 中的 JWT 令牌（主要用于 SSE/WebSocket 流）。
        auth_header: 标准 OAuth2 Bearer 令牌。
        db: 数据库会话。

    Returns:
        User: 已认证的用户对象。

    Raises:
        HTTPException: 令牌无效、过期或用户不存在。
    """
    final_token = token or auth_header
    if not final_token:
        raise HTTPException(status_code=401, detail='Not authenticated')

    return auth_service.auth_get_current_user(db, final_token)


def RoleRequired(allowed_roles: List[str]):
    """基于角色的 RBAC 校验卫兵。

    直接从令牌载荷中提取角色信息，减少数据库查询。
    支持 SYSTEM_ADMIN 超级权限。

    Args:
        allowed_roles: 允许访问的角色标识列表

    Returns:
        依赖注入函数
    """
    async def role_checker(
        token: Optional[str] = Query(None),
        auth_header: Optional[str] = Depends(optional_oauth2_scheme),
        db: Session = Depends(get_auth_db)
    ) -> User:
        final_token = token or auth_header
        if not final_token:
            raise HTTPException(status_code=401, detail='Not authenticated')

        payload = auth_service.auth_decode_access_token(final_token)
        if not payload:
            raise HTTPException(status_code=401, detail='Invalid or expired token')

        user_roles = payload.get('roles', [])

        # 超管直接放行
        if security.ADMIN_ROLE_KEY in user_roles:
            return auth_service.auth_get_current_user(db, final_token)

        if not any(role in allowed_roles for role in user_roles):
            logger.warning(f"Role Denied: User {payload.get('sub')} lacks required roles {allowed_roles}")
            raise HTTPException(
                status_code=403,
                detail=f'Permission Denied: Required roles: {allowed_roles}'
            )

        return auth_service.auth_get_current_user(db, final_token)

    return role_checker


def PermissionRequired(required_perms: List[str]):
    """基于权限标识的 RBAC 校验卫兵 (RBAC 2.0)。

    校验用户是否拥有指定的权限点（权限点已在登录时注入 JWT 载荷）。

    Args:
        required_perms: 要求的权限标识列表 (满足任一即可)

    Returns:
        依赖注入函数
    """
    async def permission_checker(
        token: Optional[str] = Query(None),
        auth_header: Optional[str] = Depends(optional_oauth2_scheme),
        db: Session = Depends(get_auth_db)
    ) -> User:
        final_token = token or auth_header
        if not final_token:
            raise HTTPException(status_code=401, detail='Not authenticated')

        payload = auth_service.auth_decode_access_token(final_token)
        if not payload:
            raise HTTPException(status_code=401, detail='Invalid or expired token')

        user_roles = payload.get('roles', [])
        user_perms = payload.get('permissions', [])

        # 超管通配符放行
        if security.ADMIN_ROLE_KEY in user_roles:
            return auth_service.auth_get_current_user(db, final_token)

        if security.ADMIN_PERMISSION_WILDCARD in user_perms:
            return auth_service.auth_get_current_user(db, final_token)

        # 检查是否满足任一权限
        if not any(perm in user_perms for perm in required_perms):
            logger.warning(
                f"Permission Denied: User {payload.get('sub')} lacks permissions {required_perms}"
            )
            raise HTTPException(
                status_code=403,
                detail=f'Permission Denied: Missing permissions {required_perms}'
            )

        return auth_service.auth_get_current_user(db, final_token)

    return permission_checker


def check_permission(required_roles: List[str]):
    """[向下兼容] 旧版权限校验，使用 RoleRequired。"""
    return RoleRequired(required_roles)


def get_user_data_scope_ids(user: User) -> List[str]:
    """[P4] 获取用户数据权限范围内的所有地点 ID (含子级)。"""
    return security.get_user_data_scope_ids(user)


def get_user_org_scope_ids(current_user: User) -> List[str]:
    """获取用户组织权限范围内的所有部门 ID (支持无限级向下递归)。"""
    db = AuthSessionLocal()
    try:
        return security.get_user_org_scope_ids(db, current_user)
    finally:
        db.close()


def get_user_permissions(current_user: User) -> List[str]:
    """获取用户所有权限标识 (含角色继承)。"""
    db = AuthSessionLocal()
    try:
        return security.get_user_permissions(db, current_user)
    finally:
        db.close()


def filter_issues_by_province(
    issues: List[Dict[str, Any]],
    current_user: User
) -> List[Dict[str, Any]]:
    """[P4 升级版] 基于 MDM Location 树进行数据权限隔离。

    - 全国权限 (Global): user.location 为空 -> 返回全量
    - 级联权限 (Regional): 返回用户所属地点及其所有下级地点的数据
    """
    user_location = getattr(current_user, 'location', None)
    if not user_location:
        return issues

    scope_loc_ids = get_user_data_scope_ids(current_user)
    db = AuthSessionLocal()
    try:
        scope_short_names = [
            loc.short_name for loc in
            db.query(Location.short_name).filter(Location.location_id.in_(scope_loc_ids)).all()
        ]
    finally:
        db.close()

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
    issues: List[Dict[str, Any]],
    current_user: User
) -> List[Dict[str, Any]]:
    """综合维度数据权限隔离（地域 + 组织）。

    依据登录用户的 MDM 属性应用双重过滤机制：
    1. 地域过滤：基于地理位置树进行级联控制 (Region Tree)。
    2. 组织过滤：基于部门 ID 进行无限级向下递归控制 (Dept Tree)。

    Args:
        issues: 原始 GitLab Issue 列表。
        current_user: 当前请求用户对象。

    Returns:
        过滤后有权访问的 Issue 列表。
    """
    filtered_by_loc = filter_issues_by_province(issues, current_user)

    user_dept_id = getattr(current_user, 'department_id', None)
    if not user_dept_id:
        return filtered_by_loc

    scope_org_ids = get_user_org_scope_ids(current_user)

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


class DataScopeFilter:
    """行级数据权限过滤器的依赖注入封装。

    使用示例:
        @router.get("/projects")
        async def list_projects(
            current_user: User = Depends(PermissionRequired(['product:project:list'])),
            data_filter: DataScopeFilter = Depends(),
            db: Session = Depends(get_db)
        ):
            query = db.query(ProjectMaster)
            query = data_filter.apply(db, query, ProjectMaster, current_user)
            return query.all()
    """

    def apply(
        self,
        db: Session,
        query,
        model_class,
        current_user: User,
        dept_field: str = 'org_id',
        owner_field: str = 'create_by'
    ):
        """应用行级数据权限过滤。

        Args:
            db: 数据库会话
            query: SQLAlchemy 查询对象
            model_class: 模型类
            current_user: 当前用户
            dept_field: 部门字段名
            owner_field: 创建人字段名

        Returns:
            过滤后的查询对象
        """
        return security.apply_row_level_security(
            db, query, model_class, current_user, dept_field, owner_field
        )

    def apply_plugin_filter(self, db: Session, query, model_class, current_user: User):
        """应用插件数据隔离过滤 (兼容旧版)。"""
        return security.apply_plugin_privacy_filter(db, query, model_class, current_user)
# -*- coding: utf-8 -*-
"""Shared dependencies and utility functions for API routers."""

import logging
from typing import List, Dict, Any, Optional, Union
from fastapi import Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from devops_collector.auth import services as auth_services
from devops_collector.auth import router as auth_router
from devops_collector.core import security
from devops_collector.auth.database import SessionLocal
from devops_collector.models.base_models import Location, User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(
    token: Optional[str] = Query(None),
    auth_header: str = Depends(oauth2_scheme),
    db: Session = Depends(auth_router.get_db)
):
    """获取并校验当前 MDM 认证用户。

    支持通过请求头 (Authorization) 或 URL 查询参数 (token) 进行身份校验。

    Args:
        token: URL 中的 JWT 令牌（SSE 流支持）。
        auth_header: 标准 OAuth2 Bearer 令牌头。
        db: 数据库会话。

    Returns:
        User: 已认证的用户数据库对象。

    Raises:
        HTTPException: 令牌无效、过期或用户不存在。
    """
    final_token = token or auth_header
    if not final_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = auth_services.jwt.decode(final_token, auth_services.SECRET_KEY, algorithms=[auth_services.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except auth_services.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = auth_services.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def check_permission(required_roles: List[str]):
    """[P5] RBAC 权限校验依赖项构造器。
    
    校验逻辑：
    1. 必须是已登录用户。
    2. 如果用户具备 'SYSTEM_ADMIN' 角色，则拥有全量权限。
    3. 否则，用户所属的角色编码 (Role.code) 必须在 required_roles 列表中。
    """
    async def permission_checker(current_user: User = Depends(get_current_user)):
        user_role_codes = [r.code for r in current_user.roles]
        
        # 1. 超级管理员绿灯
        if 'SYSTEM_ADMIN' in user_role_codes:
            return current_user
        
        # 2. 角色匹配校验
        has_permission = any(role_code in required_roles for role_code in user_role_codes)
        
        if not has_permission:
            logger.warning(
                f"Access Denied: User {current_user.primary_email} (Roles: {user_role_codes}) "
                f"attempted restricted action. Required roles: {required_roles}"
            )
            raise HTTPException(
                status_code=403, 
                detail=f"Permission Denied: Required roles: {required_roles}"
            )
        return current_user
    return permission_checker

def get_user_data_scope_ids(user) -> List[str]:
    """[P4] 获取用户数据权限范围内的所有地点 ID (含子级)。"""
    user_location = getattr(user, 'location', None)
    if not user_location:
        return [] # 全国权限（通过短名称 '全国' 判断，此处返回 ID 为空）
    
    # 递归收集所有子级 ID
    scope_ids = [user_location.location_id]
    
    def collect_children(loc):
        for child in loc.children:
            scope_ids.append(child.location_id)
            collect_children(child)
            
    collect_children(user_location)
    return scope_ids

def get_user_org_scope_ids(current_user) -> List[str]:
    """获取用户组织权限范围内的所有部门 ID (支持无限级向下递归)。"""
    db = SessionLocal()
    try:
        return security.get_user_org_scope_ids(db, current_user)
    finally:
        db.close()

def filter_issues_by_province(issues: List[Dict[str, Any]], current_user) -> List[Dict[str, Any]]:
    """[P4 升级版] 基于 MDM Location 树进行数据权限隔离。
    
    - 全国权限 (Global): user.location 为空 -> 返回全量
    - 级联权限 (Regional): 返回用户所属地点及其所有下级地点的数据
    """
    user_location = getattr(current_user, 'location', None)
    
    # 如果没有 location 记录，视为集团/全国权限
    if not user_location:
        return issues
        
    # 获取用户的数据覆盖范围 (当前地点 + 所有子地点)
    scope_loc_ids = get_user_data_scope_ids(current_user)
    
    # 获取用户地点的短名称列表，用于向下兼容基于标签字符串的过滤
    # 在 MDM 中，我们倾向于使用 ID，但当前 GitLab 标签存储的是短名称（如 'guangdong'）
    # 我们通过查询数据库获取这些 ID 对应的短名称
    
    db = SessionLocal()
    try:
        scope_short_names = [
            loc.short_name for loc in db.query(Location.short_name).filter(Location.location_id.in_(scope_loc_ids)).all()
        ]
    finally:
        db.close()

    filtered = []
    for issue in issues:
        labels = issue.get('labels', [])
        province_tag = "nationwide"
        for l in labels:
            if l.startswith("province::"):
                province_tag = l.split("::")[1]
                break
        
        # 匹配逻辑：如果标签中的地点名称在用户的数据范围内，则允许访问
        if province_tag in scope_short_names:
            filtered.append(issue)
            
    return filtered

def filter_issues_by_privacy(issues: List[Dict[str, Any]], current_user) -> List[Dict[str, Any]]:
    """综合维度数据权限隔离（地域 + 组织）。

    依据登录用户的 MDM 属性应用双重过滤机制：
    1. 地域过滤：基于地理位置树进行级联控制 (Region Tree)。
    2. 组织过滤：基于部门 ID 进行无限级向下递归控制 (Dept Tree)。

    Args:
        issues (List[Dict[str, Any]]): 原始 GitLab Issue 列表。
        current_user (User): 当前请求用户对象。

    Returns:
        List[Dict[str, Any]]: 过滤后有权访问的 Issue 列表。
    """
    # 1. 地域过滤
    filtered_by_loc = filter_issues_by_province(issues, current_user)
    
    # 2. 组织过滤
    user_dept_id = getattr(current_user, 'department_id', None)
    if not user_dept_id:
        return filtered_by_loc
        
    scope_org_ids = get_user_org_scope_ids(current_user)
    
    final_filtered = []
    for issue in filtered_by_loc:
        labels = issue.get('labels', [])
        dept_tag = None
        for l in labels:
            if l.startswith("dept::"):
                dept_tag = l.split("::")[1]
                break
        
        # 如果没有部门标签，视为公共数据或尚未归类，保留输出
        # 如果有部门标签，则必须在授权范围内
        if not dept_tag or dept_tag in scope_org_ids:
            final_filtered.append(issue)
            
    return final_filtered

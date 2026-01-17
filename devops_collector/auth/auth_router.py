"""认证模块路由。

处理用户注册、登录、获取当前用户信息以及 GitLab OAuth 绑定。
"""
from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy.orm import Session
from devops_collector.auth import auth_service, auth_schema
from devops_collector.models.base_models import User, UserOAuthToken
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.config import settings

# 初始化认证模块路由
auth_router = APIRouter(prefix='/auth', tags=['Authentication'])


@auth_router.get('/gitlab/bind')
async def auth_bind_gitlab(
    request: Request, 
    token: str = Depends(auth_service.auth_oauth2_scheme), 
    db: Session = Depends(get_auth_db)
):
    """发起 GitLab OAuth 绑定。
    
    Args:
        request: FastAPI 请求对象。
        token: 用户的 JWT 令牌。
        db: 数据库会话。
        
    Returns:
        RedirectResponse: 重定向到 GitLab 授权页面。
        
    Raises:
        HTTPException: 配置错误或令牌无效。
    """
    if not settings.gitlab.client_id or not settings.gitlab.redirect_uri:
        raise HTTPException(500, 'GitLab OAuth not configured')
        
    payload = auth_service.auth_decode_access_token(token)
    if not payload:
        raise HTTPException(401, 'Invalid or expired token')
    
    email: str = payload.get('sub')
    current_user = auth_service.auth_get_user_by_email(db, email=email)
    if not current_user:
        raise HTTPException(401, 'User not found')
    
    state = str(current_user.global_user_id)
    auth_url = (
        f'{settings.gitlab.url}/oauth/authorize?'
        f'client_id={settings.gitlab.client_id}&'
        f'redirect_uri={settings.gitlab.redirect_uri}&'
        f'response_type=code&scope=api&state={state}'
    )
    return RedirectResponse(auth_url)

@auth_router.get('/gitlab/callback')
async def auth_gitlab_callback(code: str, state: str = None, db: Session = Depends(get_auth_db)):
    """GitLab OAuth 回调处理。
    
    Args:
        code: GitLab 返回的授权码。
        state: 传递的 global_user_id。
        db: 数据库会话。
        
    Returns:
        RedirectResponse: 绑定成功后的重定向。
        
    Raises:
        HTTPException: GitLab 认证失败或状态异常。
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'{settings.gitlab.url}/oauth/token', 
            data={
                'client_id': settings.gitlab.client_id, 
                'client_secret': settings.gitlab.client_secret, 
                'code': code, 
                'grant_type': 'authorization_code', 
                'redirect_uri': settings.gitlab.redirect_uri
            }
        )
        if resp.status_code != 200:
            raise HTTPException(400, f'GitLab Auth Failed: {resp.text}')
        token_data = resp.json()
    
    user_id = state
    if not user_id:
        raise HTTPException(400, 'Invalid State')
    
    auth_service.auth_upsert_gitlab_token(db, user_id, token_data)
    return RedirectResponse(url='/iteration_plan.html?bind_success=true')

@auth_router.post('/register', response_model=auth_schema.AuthUserResponse)
def auth_register(user: auth_schema.AuthRegisterRequest, db: Session = Depends(get_auth_db)):
    """注册新用户。
    
    Args:
        user: 注册请求数据模型。
        db: 数据库会话。
        
    Returns:
        AuthUserResponse: 注册成功后的用户信息。
        
    Raises:
        HTTPException: 域名不支持或用户已存在。
    """
    # 验证邮箱域名
    if not auth_service.auth_validate_email_domain(user.email):
        allowed = ", ".join(settings.auth.allowed_domains)
        raise HTTPException(
            status_code=400, 
            detail=f'仅支持以下域名的公司邮箱注册: {allowed}'
        )
    
    db_user = auth_service.auth_get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail='Email already registered')
    return auth_service.auth_create_user(db=db, user_data=user)

@auth_router.post('/login', response_model=auth_schema.AuthToken)
def auth_login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_auth_db)):
    """登录获取访问令牌。
    
    RBAC 2.0: 从 SysRole + SysMenu 聚合权限，支持角色继承。
    
    Args:
        form_data: 表单数据。
        db: 数据库会话。
        
    Returns:
        AuthToken: 包含访问令牌的响应。
        
    Raises:
        HTTPException: 用户名或密码错误。
    """
    from devops_collector.core import security
    
    user = auth_service.auth_authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail='Incorrect username or password', 
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # RBAC 2.0: 获取用户角色标识列表
    user_roles = [r.role_key for r in user.roles] if user.roles else []
    
    # RBAC 2.0: 聚合用户所有角色的权限标识 (含角色继承)
    user_permissions = security.get_user_permissions(db, user)
    
    # RBAC 2.0: 获取用户有效的数据范围
    data_scope = security.get_user_effective_data_scope(db, user)
    
    token_data = {
        'sub': user.primary_email,
        'user_id': str(user.global_user_id),
        'username': user.username,
        'full_name': user.full_name,
        'department_id': user.department_id,
        'roles': user_roles,
        'permissions': user_permissions,
        'data_scope': data_scope
    }
    
    access_token = auth_service.auth_create_access_token(
        data=token_data, 
        expires_delta=access_token_expires
    )
    return {'access_token': access_token, 'token_type': 'bearer'}

@auth_router.get('/me', response_model=auth_schema.AuthUserResponse)
def auth_read_users_me(token: str = Depends(auth_service.auth_oauth2_scheme), db: Session = Depends(get_auth_db)):
    """获取当前登录用户信息。
    
    Args:
        token: JWT 令牌。
        db: 数据库会话。
        
    Returns:
        AuthUserResponse: 包含 GitLab 连接状态的用户信息。
        
    Raises:
        HTTPException: 令牌无效或用户未找到。
    """
    user = auth_service.auth_get_current_user(db, token)
    token_obj = auth_service.auth_get_gitlab_token(db, user.global_user_id)
    
    resp = auth_schema.AuthUserResponse.model_validate(user)
    resp.gitlab_connected = True if token_obj else False
    return resp

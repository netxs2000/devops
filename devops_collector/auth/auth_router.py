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
from devops_collector.auth.auth_database import AuthSessionLocal
from devops_collector.config import Config

# 初始化认证模块路由
auth_router = APIRouter(prefix='/auth', tags=['Authentication'])

def get_auth_db():
    """获取认证模块数据库会话的依赖项。"""
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()

@auth_router.get('/gitlab/bind')
async def auth_bind_gitlab(request: Request, token: str = Depends(auth_service.auth_oauth2_scheme), db: Session = Depends(get_auth_db)):
    """发起 GitLab OAuth 绑定。"""
    if not Config.GITLAB_CLIENT_ID or not Config.GITLAB_REDIRECT_URI:
        raise HTTPException(500, 'GitLab OAuth not configured')
    try:
        payload = auth_service.jwt.decode(token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
        email: str = payload.get('sub')
        current_user = auth_service.auth_get_user_by_email(db, email=email)
        if not current_user:
            raise HTTPException(401, 'User not found')
    except Exception:
        raise HTTPException(401, 'Invalid token')
    
    state = str(current_user.global_user_id)
    auth_url = (
        f'{Config.GITLAB_URL}/oauth/authorize?'
        f'client_id={Config.GITLAB_CLIENT_ID}&'
        f'redirect_uri={Config.GITLAB_REDIRECT_URI}&'
        f'response_type=code&scope=api&state={state}'
    )
    return RedirectResponse(auth_url)

@auth_router.get('/gitlab/callback')
async def auth_gitlab_callback(code: str, state: str = None, db: Session = Depends(get_auth_db)):
    """GitLab OAuth 回调处理。"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f'{Config.GITLAB_URL}/oauth/token', 
            data={
                'client_id': Config.GITLAB_CLIENT_ID, 
                'client_secret': Config.GITLAB_CLIENT_SECRET, 
                'code': code, 
                'grant_type': 'authorization_code', 
                'redirect_uri': Config.GITLAB_REDIRECT_URI
            }
        )
        if resp.status_code != 200:
            raise HTTPException(400, f'GitLab Auth Failed: {resp.text}')
        token_data = resp.json()
    
    user_id = state
    if not user_id:
        raise HTTPException(400, 'Invalid State')
    
    token_rec = db.query(UserOAuthToken).filter_by(user_id=user_id, provider='gitlab').first()
    if not token_rec:
        token_rec = UserOAuthToken(
            user_id=user_id, 
            provider='gitlab', 
            access_token=token_data['access_token'], 
            token_type=token_data.get('token_type', 'Bearer')
        )
        db.add(token_rec)
    else:
        token_rec.access_token = token_data['access_token']
        token_rec.updated_at = datetime.now()
    db.commit()
    return RedirectResponse(url='/static/iteration.html?bind_success=true')

@auth_router.post('/register', response_model=auth_schema.AuthUserResponse)
def auth_register(user: auth_schema.AuthRegisterRequest, db: Session = Depends(get_auth_db)):
    """注册新用户。"""
    # 验证邮箱域名
    if not auth_service.auth_validate_email_domain(user.email):
        allowed = ", ".join(Config.AUTH_ALLOWED_DOMAINS)
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
    """登录获取访问令牌。"""
    user = auth_service.auth_authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail='Incorrect username or password', 
            headers={'WWW-Authenticate': 'Bearer'}
        )
    access_token_expires = timedelta(minutes=auth_service.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.auth_create_access_token(
        data={'sub': user.primary_email, 'user_id': str(user.global_user_id)}, 
        expires_delta=access_token_expires
    )
    return {'access_token': access_token, 'token_type': 'bearer'}

@auth_router.get('/me', response_model=auth_schema.AuthUserResponse)
def auth_read_users_me(token: str = Depends(auth_service.auth_oauth2_scheme), db: Session = Depends(get_auth_db)):
    """获取当前登录用户信息。"""
    try:
        payload = auth_service.jwt.decode(token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
        email: str = payload.get('sub')
        if email is None:
            raise HTTPException(status_code=401, detail='Invalid token')
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid token')
    
    user = auth_service.auth_get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=401, detail='User not found')
    
    token_obj = db.query(UserOAuthToken).filter_by(user_id=user.global_user_id, provider='gitlab').first()
    resp = auth_schema.AuthUserResponse.model_validate(user)
    resp.gitlab_connected = True if token_obj else False
    return resp

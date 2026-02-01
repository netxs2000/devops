"""认证模块核心服务。

实现用户鉴权、密码哈希处理、令牌生成以及核心业务校验（如域名过滤）。
"""
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import httpx
from devops_collector.models.base_models import User, UserCredential
from devops_collector.config import settings, Config
from uuid import UUID
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.auth import auth_schema

# 配置日志
logger = logging.getLogger(__name__)

# 安全配置使用 settings 统一管理
SECRET_KEY = settings.auth.secret_key
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
auth_pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
auth_oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')

def auth_decode_access_token(token: str) -> Optional[dict]:
    """解码并验证 JWT 访问令牌。
    
    Args:
        token: JWT 令牌字符串。
        
    Returns:
        Optional[dict]: 令牌载荷，验证失败则返回 None。
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def auth_verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否与哈希密码匹配。
    
    Args:
        plain_password: 明文密码。
        hashed_password: 哈希后的密码。
        
    Returns:
        bool: 是否匹配。
    """
    return auth_pwd_context.verify(plain_password, hashed_password)

def auth_get_password_hash(password: str) -> str:
    """生成密码的 BCRPYT 哈希。
    
    Args:
        password: 明文密码。
        
    Returns:
        str: 哈希后的密码。
    """
    return auth_pwd_context.hash(password)

def auth_create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT 访问令牌。
    
    Args:
        data: 需要加密到令牌中的数据。
        expires_delta: 令牌有效期。
        
    Returns:
        str: 编码后的 JWT 字符串。
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    for k, v in to_encode.items():
        if isinstance(v, (UUID, uuid.UUID)):
            to_encode[k] = str(v)
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def auth_get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据主邮箱获取当前有效用户。
    
    Args:
        db: 数据库会话。
        email: 用户邮箱。
        
    Returns:
        Optional[User]: 用户对象，如果不存在则返回 None。
    """
    return db.query(User).filter(User.primary_email == email, User.is_current == True).first()

def auth_validate_email_domain(email: str) -> bool:
    """验证邮箱域名是否在允许的列表中。
    
    Args:
        email: 待验证的邮箱地址。
        
    Returns:
        bool: 验证通过返回 True，否则返回 False。
    """
    if not email or '@' not in email:
        return False
    domain = email.split('@')[-1].lower()
    return domain in settings.auth.allowed_domains

def auth_create_user(db: Session, user_data: Any) -> User:
    """创建新用户及其认证凭据。
    
    Args:
        db: 数据库会话。
        user_data: 包含用户注册信息的对象。
        
    Returns:
        User: 创建后的用户对象。
    """
    hashed_password = auth_get_password_hash(user_data.password)
    db_user = User(
        global_user_id=uuid.uuid4(), 
        primary_email=user_data.email, 
        full_name=user_data.full_name, 
        employee_id=user_data.employee_id, 
        is_active=False, 
        is_survivor=True, 
        sync_version=1, 
        is_current=True, 
        is_deleted=False
    )
    db.add(db_user)
    db.flush()
    db_cred = UserCredential(user_id=db_user.global_user_id, password_hash=hashed_password)
    db.add(db_cred)
    db.commit()
    db.refresh(db_user)
    return db_user

def auth_authenticate_user(db: Session, email: str, password: str) -> Union[User, bool]:
    """验证用户凭据并返回用户对象。
    
    Args:
        db: 数据库会话。
        email: 用户邮箱。
        password: 密码。
        
    Returns:
        Union[User, bool]: 验证成功返回 User 对象，失败返回 False。
    """
    user = auth_get_user_by_email(db, email)
    if not user:
        return False
    if not user.credential:
        return False
    if not auth_verify_password(password, user.credential.password_hash):
        return False
    return user

def auth_get_gitlab_token(db: Session, user_id: Any) -> Optional[Any]:
    """获取用户的 GitLab OAuth 令牌。
    
    Args:
        db: 数据库会话。
        user_id: 全局用户 ID。
        
    Returns:
        Optional[UserOAuthToken]: 令牌对象。
    """
    from devops_collector.models.base_models import UserOAuthToken
    return db.query(UserOAuthToken).filter_by(user_id=str(user_id), provider='gitlab').first()

def auth_upsert_gitlab_token(db: Session, user_id: Any, token_data: dict) -> Any:
    """更新或创建用户的 GitLab OAuth 令牌。
    
    Args:
        db: 数据库会话。
        user_id: 全局用户 ID。
        token_data: 包含 access_token 和 token_type 的字典。
        
    Returns:
        UserOAuthToken: 更新或创建后的令牌对象。
    """
    from devops_collector.models.base_models import UserOAuthToken
    token_rec = auth_get_gitlab_token(db, user_id)
    if not token_rec:
        token_rec = UserOAuthToken(
            user_id=str(user_id),
            provider='gitlab',
            access_token=token_data['access_token'],
            token_type=token_data.get('token_type', 'Bearer')
        )
        db.add(token_rec)
    else:
        token_rec.access_token = token_data['access_token']
        token_rec.updated_at = datetime.now()
    db.commit()
    return token_rec

def auth_get_current_user(db: Session, token: str) -> User:
    """获取并校验当前认证用户。
    
    Args:
        db: 数据库会话。
        token: JWT 令牌字符串。
        
    Returns:
        User: 当前认证的用户对象。
        
    Raises:
        HTTPException: 身份验证失败。
    """
    payload = auth_decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail='Invalid token or expired')
    
    email: str = payload.get('sub')
    if email is None:
        raise HTTPException(status_code=401, detail='Invalid token')
        
    user = auth_get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=401, detail='User not found')
    return user

def get_current_user_obj(
    token: str = Depends(auth_oauth2_scheme), 
    db: Session = Depends(get_auth_db)
) -> User:
    """FastAPI 依赖项：获取并校验当前已登录用户。
    
    Args:
        token: JWT 令牌。
        db: 数据库会话。
        
    Returns:
        User: 用户对象。
    """
    return auth_get_current_user(db, token)

def auth_get_current_active_user(current_user: User = Depends(get_current_user_obj)) -> User:
    """FastAPI 依赖项：验证当前用户是否处于激活状态。
    
    Args:
        current_user: 当前用户对象。
        
    Returns:
        User: 激活状态的用户对象。
        
    Raises:
        HTTPException: 用户已禁用。
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail='Inactive user')
    return current_user

async def auth_process_gitlab_callback(db: Session, code: str) -> dict:
    """处理 GitLab OAuth 回调的核心业务逻辑。
    
    包含：换取 Token、获取并校验用户信息、查找/创建用户、生成系统 JWT。
    
    Args:
        db: 数据库会话
        code: GitLab 授权码
        
    Returns:
        dict: 结果字典，包含 redirect_url 或错误信息
    """
    from devops_collector.core import security
    
    # 1. 换取 Token
    async with httpx.AsyncClient(verify=settings.gitlab.verify_ssl) as client:
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
            logger.error(f"GitLab OAuth Token Exchange Failed: {resp.text}")
            return {"error": "token_exchange_failed"}
        token_data = resp.json()

    # 2. 获取用户信息
    async with httpx.AsyncClient(verify=settings.gitlab.verify_ssl) as client:
        user_resp = await client.get(
            f'{settings.gitlab.url}/api/v4/user',
            headers={'Authorization': f'Bearer {token_data["access_token"]}'}
        )
        if user_resp.status_code != 200:
            return {"error": "user_info_failed"}
        gitlab_user = user_resp.json()

    email = gitlab_user.get('email')
    full_name = gitlab_user.get('name') or gitlab_user.get('username')
    
    if not email:
        return {"error": "email_missing"}

    # 3. 校验邮箱域名
    if not auth_validate_email_domain(email):
        return {"error": "domain_not_allowed"}

    # 4. 查找或创建用户
    user = auth_get_user_by_email(db, email)
    
    if not user:
        # 自动创建待审批账户
        user = auth_create_user(
            db=db, 
            user_data=auth_schema.AuthRegisterRequest(
                email=email,
                password=security.generate_random_password(),
                full_name=full_name,
                employee_id=None
            )
        )
        user.is_active = False
        db.commit()
        logger.info(f"New pending user created via GitLab OAuth: {email}")

    # 5. 更新用户的 GitLab Token
    auth_upsert_gitlab_token(db, str(user.global_user_id), token_data)

    # 6. 如果用户未激活，返回 pending 状态
    if not user.is_active:
        return {"state": "pending"}

    # 7. 生成本系统 JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    user_roles = [r.role_key for r in user.roles] if user.roles else []
    user_permissions = security.get_user_permissions(db, user)
    data_scope = security.get_user_effective_data_scope(db, user)
    
    token_payload = {
        'sub': user.primary_email,
        'user_id': str(user.global_user_id),
        'username': user.username or email.split('@')[0],
        'full_name': user.full_name,
        'department_id': user.department_id,
        'roles': user_roles,
        'permissions': user_permissions,
        'data_scope': data_scope
    }
    
    access_token = auth_create_access_token(
        data=token_payload, 
        expires_delta=access_token_expires
    )

    return {"access_token": access_token}

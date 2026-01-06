import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from devops_collector.models.base_models import User, UserCredential
from devops_collector.config import Config
from uuid import UUID

SECRET_KEY = getattr(Config, 'SECRET_KEY', 'your-secret-key-keep-it-secret')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否与哈希密码匹配。"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码的 BCRPYT 哈希。"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT 访问令牌。"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    for k, v in to_encode.items():
        if isinstance(v, (UUID, uuid.UUID)):
            to_encode[k] = str(v)
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据主邮箱获取当前有效用户。"""
    return db.query(User).filter(User.primary_email == email, User.is_current == True).first()

def create_user(db: Session, user_data: Any) -> User:
    """创建新用户及其认证凭据。"""
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        global_user_id=uuid.uuid4(), 
        primary_email=user_data.email, 
        full_name=user_data.full_name, 
        employee_id=user_data.employee_id, 
        is_active=True, 
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

def authenticate_user(db: Session, email: str, password: str) -> Union[User, bool]:
    """验证用户凭据并返回用户对象。"""
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not user.credential:
        return False
    if not verify_password(password, user.credential.password_hash):
        return False
    return user

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """FastAPI 依赖项：从令牌中获取当前认证用户。"""
    from devops_collector.auth.database import SessionLocal
    auth_db = SessionLocal()
    try:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get('sub')
            if email is None:
                raise HTTPException(status_code=401, detail='Could not validate credentials')
        except JWTError:
            raise HTTPException(status_code=401, detail='Could not validate credentials')
        user = get_user_by_email(auth_db, email=email)
        if user is None:
            raise HTTPException(status_code=401, detail='User not found')
        return user
    finally:
        auth_db.close()

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI 依赖项：验证当前用户是否处于激活状态。"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail='Inactive user')
    return current_user
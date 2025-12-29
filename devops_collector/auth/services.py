from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from devops_collector.models.base_models import User, UserCredential
from devops_collector.config import Config
from uuid import UUID

SECRET_KEY = getattr(Config, "SECRET_KEY", "your-secret-key-keep-it-secret") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    # Convert UUIDs to strings in JWT
    for k, v in to_encode.items():
        if isinstance(v, UUID):
            to_encode[k] = str(v)
            
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.primary_email == email).first()

def create_user(db: Session, user_data):
    hashed_password = get_password_hash(user_data.password)
    
    db_user = User(
        primary_email=user_data.email,
        full_name=user_data.full_name,
        employee_id=user_data.employee_id,
        is_active=True
    )
    db.add(db_user)
    db.flush() # Generate ID
    
    db_cred = UserCredential(
        user_id=db_user.global_user_id,
        password_hash=hashed_password
    )
    db.add(db_cred)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not user.credential:
         return False
    if not verify_password(password, user.credential.password_hash):
        return False
    return user

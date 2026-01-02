"""TODO: Add module description."""
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
SECRET_KEY = getattr(Config, 'SECRET_KEY', 'your-secret-key-keep-it-secret')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')

def verify_password(plain_password, hashed_password):
    '''"""TODO: Add description.

Args:
    plain_password: TODO
    hashed_password: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    '''"""TODO: Add description.

Args:
    password: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta]=None):
    '''"""TODO: Add description.

Args:
    data: TODO
    expires_delta: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    for k, v in to_encode.items():
        if isinstance(v, UUID):
            to_encode[k] = str(v)
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(db: Session, email: str):
    '''"""TODO: Add description.

Args:
    db: TODO
    email: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    return db.query(User).filter(User.primary_email == email, User.is_current == True).first()

def create_user(db: Session, user_data):
    '''"""TODO: Add description.

Args:
    db: TODO
    user_data: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    hashed_password = get_password_hash(user_data.password)
    db_user = User(global_user_id=uuid.uuid4(), primary_email=user_data.email, full_name=user_data.full_name, employee_id=user_data.employee_id, is_active=True, is_survivor=True, sync_version=1, is_current=True, is_deleted=False)
    db.add(db_user)
    db.flush()
    db_cred = UserCredential(user_id=db_user.global_user_id, password_hash=hashed_password)
    db.add(db_cred)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    '''"""TODO: Add description.

Args:
    db: TODO
    email: TODO
    password: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not user.credential:
        return False
    if not verify_password(password, user.credential.password_hash):
        return False
    return user

def get_current_user(token: str=Depends(oauth2_scheme)):
    '''"""TODO: Add description.

Args:
    token: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
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

def get_current_active_user(current_user: User=Depends(get_current_user)):
    '''"""TODO: Add description.

Args:
    current_user: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail='Inactive user')
    return current_user
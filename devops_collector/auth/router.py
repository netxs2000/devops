from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
import httpx
from sqlalchemy.orm import Session

from devops_collector.auth import services, schemas
from devops_collector.models.base_models import User, UserOAuthToken
from devops_collector.auth.database import SessionLocal
from devops_collector.core.config import Config

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/gitlab/bind")
async def bind_gitlab(
    request: Request,
    token: str = Depends(services.oauth2_scheme), # 获取当前登录用户
    db: Session = Depends(get_db)
):
    """发起 GitLab OAuth 绑定。"""
    if not Config.GITLAB_CLIENT_ID or not Config.GITLAB_REDIRECT_URI:
        raise HTTPException(500, "GitLab OAuth not configured")
        
    # 获取当前用户
    try:
        payload = services.jwt.decode(token, services.SECRET_KEY, algorithms=[services.ALGORITHM])
        email: str = payload.get("sub")
        current_user = services.get_user_by_email(db, email=email)
        if not current_user:
             raise HTTPException(401, "User not found")
    except Exception:
        raise HTTPException(401, "Invalid token")
    
    state = str(current_user.global_user_id)
    
    auth_url = (
        f"{Config.GITLAB_URL}/oauth/authorize"
        f"?client_id={Config.GITLAB_CLIENT_ID}"
        f"&redirect_uri={Config.GITLAB_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=api"
        f"&state={state}"
    )
    return RedirectResponse(auth_url)

@router.get("/gitlab/callback")
async def gitlab_callback(
    code: str,
    state: str = None,
    db: Session = Depends(get_db)
):
    """GitLab OAuth 回调处理。"""
    # 1. Exchange code for access token
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{Config.GITLAB_URL}/oauth/token", data={
            "client_id": Config.GITLAB_CLIENT_ID,
            "client_secret": Config.GITLAB_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": Config.GITLAB_REDIRECT_URI
        })
        if resp.status_code != 200:
            raise HTTPException(400, f"GitLab Auth Failed: {resp.text}")
        token_data = resp.json()
    
    # 2. Identify User
    user_id = state 
    if not user_id:
         raise HTTPException(400, "Invalid State")
         
    # 3. Save/Update Token
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
    
    return RedirectResponse(url="/static/iteration.html?bind_success=true")

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserRegisterRequest, db: Session = Depends(get_db)):
    db_user = services.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return services.create_user(db=db, user_data=user)

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = services.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=services.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = services.create_access_token(
        data={"sub": user.primary_email, "user_id": str(user.global_user_id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(token: str = Depends(services.oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = services.jwt.decode(token, services.SECRET_KEY, algorithms=[services.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    user = services.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
        
    # Check GitLab binding
    token = db.query(UserOAuthToken).filter_by(user_id=user.global_user_id, provider='gitlab').first()
    
    # Create response object manually to include computed field
    resp = schemas.UserResponse.from_orm(user)
    resp.gitlab_connected = True if token else False
    
    return resp

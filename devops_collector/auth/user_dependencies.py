"""TODO: Add module description."""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from devops_portal.dependencies import get_current_user
from devops_collector.auth.router import get_db
from devops_collector.models.base_models import User, UserOAuthToken
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.config import Config

def get_user_gitlab_client(current_user: User=Depends(get_current_user), db: Session=Depends(get_db)) -> GitLabClient:
    """依赖注入：获取基于当前登录用户 OAuth Token 的 GitLab 客户端。
    
    用于实现“持证办理”模式，即代表用户本人调用 API，而非使用系统公用 Token。
    """
    token_record = db.query(UserOAuthToken).filter_by(user_id=current_user.global_user_id, provider='gitlab').first()
    if not token_record:
        raise HTTPException(status_code=403, detail='Missing GitLab binding. Please link your GitLab account in Profile.')
    return GitLabClient(url=Config.GITLAB_URL, token=token_record.access_token)
"""认证模块依赖项。

提供基于用户身份的扩展功能支持，如 GitLab 客户端注入。
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from devops_collector.auth import auth_service
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.models.base_models import User, UserOAuthToken
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.config import settings

def get_user_gitlab_client(
    current_user: User = Depends(auth_service.get_current_user_obj), 
    db: Session = Depends(get_auth_db)
) -> GitLabClient:
    """依赖注入：获取基于当前登录用户 OAuth Token 的 GitLab 客户端。
    
    用于实现“持证办理”模式，即代表用户本人调用 API，而非使用系统公用 Token。
    
    Args:
        current_user: 当前已认证的用户。
        db: 数据库会话。
        
    Returns:
        GitLabClient: 初始化好的 GitLab 客户端。
        
    Raises:
        HTTPException: 用户未绑定 GitLab。
    """
    token_record = db.query(UserOAuthToken).filter_by(
        user_id=current_user.global_user_id, 
        provider='gitlab'
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=403, 
            detail='Missing GitLab binding. Please link your GitLab account in Profile.'
        )
    return GitLabClient(url=settings.gitlab.url, token=token_record.access_token)
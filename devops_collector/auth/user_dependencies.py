from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from devops_collector.auth.dependencies import get_current_user, get_db
from devops_collector.models.base_models import User, UserOAuthToken
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.core.config import Config

def get_user_gitlab_client(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
) -> GitLabClient:
    """依赖注入：获取基于当前登录用户 OAuth Token 的 GitLab 客户端。
    
    用于实现“持证办理”模式，即代表用户本人调用 API，而非使用系统公用 Token。
    """
    # 1. 查找用户的 GitLab Token
    token_record = db.query(UserOAuthToken).filter_by(
        user_id=current_user.global_user_id, 
        provider='gitlab'
    ).first()
    
    # 2. 校验
    if not token_record:
         # 熔断: 如果没有绑定，拒绝操作。提示用户去绑定。
         # 注意: 这里的 status_code=403 会让前端捕获
         raise HTTPException(
             status_code=403, 
             detail="Missing GitLab binding. Please link your GitLab account in Profile."
         )
         
    # 3. 初始化客户端
    # TODO: 此处可加入 Token 过期刷新逻辑 (RefreshToken)
    return GitLabClient(url=Config.GITLAB_URL, token=token_record.access_token)

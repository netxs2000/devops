"""GitLab 身份识别与匹配模块"""
import logging
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from devops_collector.models import IdentityMapping, User, Organization, Commit
from devops_collector.core.identity_manager import IdentityManager
from .client import GitLabClient

logger = logging.getLogger(__name__)

class IdentityMatcher:
    """身份匹配器，将 Commit 作者信息关联到 GitLab 用户。"""
    
    def __init__(self, session: Session):
        self.session = session
        self._build_index()
    
    def _build_index(self):
        """构建 GitLab 用户身份索引以进行规则匹配。"""
        mappings = self.session.query(IdentityMapping).filter_by(source='gitlab').all()
        
        self.email_map = {}
        self.username_map = {}
        self.name_map = {}
        
        for m in mappings:
            if m.email:
                self.email_map[m.email.lower()] = m.user_id
            if m.external_id:
                self.username_map[m.external_id.lower()] = m.user_id
            if m.external_name:
                self.name_map[m.external_name.lower()] = m.user_id
    
    def match(self, commit: Commit) -> Optional[int]:
        """按 4 级规则匹配 Commit 作者到内部用户 ID。"""
        email = commit.author_email.lower() if commit.author_email else ""
        name = commit.author_name.lower() if commit.author_name else ""
        
        if email in self.email_map:
            return self.email_map[email]
        if name in self.username_map:
            return self.username_map[name]
        if name in self.name_map:
            return self.name_map[name]
        if email and '@' in email:
            prefix = email.split('@')[0]
            if prefix in self.username_map:
                return self.username_map[prefix]
        
        user = IdentityManager.get_or_create_user(
            self.session, 
            source='gitlab_commit', 
            external_id=commit.author_email,
            email=commit.author_email,
            name=commit.author_name
        )
        return user.id


class UserResolver:
    """用户解析器，将 gitlab_id 映射到内部用户 ID。"""
    
    def __init__(self, session: Session, client: GitLabClient):
        self.session = session
        self.client = client
        self.cache: Dict[int, int] = {} 
        self._load_cache()
    
    def _load_cache(self):
        """加载现有 GitLab 映射到缓存。"""
        mappings = self.session.query(IdentityMapping).filter_by(source='gitlab').all()
        for m in mappings:
            try:
                self.cache[int(m.external_id)] = m.user_id
            except ValueError:
                continue
    
    def resolve(self, gitlab_id: int) -> Optional[int]:
        """解析 GitLab 用户 ID 到内部 ID。"""
        if gitlab_id in self.cache:
            return self.cache[gitlab_id]
        
        try:
            user_data = self.client.get_user(gitlab_id)
            user = IdentityManager.get_or_create_user(
                self.session,
                source='gitlab',
                external_id=str(gitlab_id),
                email=user_data.get('email'),
                name=user_data.get('name'),
                username=user_data.get('username')
            )
            
            # 特色逻辑：从 skype 字段提取部门
            dept_name = user_data.get('skype')
            if dept_name:
                user.department = dept_name
                org = self.session.query(Organization).filter_by(
                    name=dept_name, level='Center'
                ).first()
                if not org:
                    org = Organization(name=dept_name, level='Center')
                    self.session.add(org)
                    self.session.flush()
                user.organization_id = org.id
            
            self.session.flush()
            self.cache[gitlab_id] = user.id
            return user.id
        except Exception as e:
            logger.warning(f"Failed to resolve user {gitlab_id}: {e}")
            return None

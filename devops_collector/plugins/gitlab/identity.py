"""GitLab 身份识别与匹配模块 (支持 SCD Type 2)"""
import logging
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from devops_collector.models import IdentityMapping, User, Organization
from devops_collector.core.identity_manager import IdentityManager
logger = logging.getLogger(__name__)

class IdentityMatcher:
    """身份匹配器，将 Commit 作者信息关联到 GitLab 用户。"""

    def __init__(self, session: Session):
        '''"""TODO: Add description.

Args:
    self: TODO
    session: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.session = session
        self._build_index()

    def _build_index(self):
        """构建 GitLab 用户身份索引以进行规则匹配。"""
        mappings = self.session.query(IdentityMapping).filter_by(source_system='gitlab').all()
        self.email_map = {}
        self.username_map = {}
        self.name_map = {}
        for m in mappings:
            if m.external_email:
                self.email_map[m.external_email.lower()] = m.global_user_id
            if m.external_user_id:
                self.username_map[m.external_user_id.lower()] = m.global_user_id
            if m.external_username:
                self.name_map[m.external_username.lower()] = m.global_user_id

    def match(self, commit: Any) -> Optional[Any]:
        """按 4 级规则匹配 Commit 作者到内部用户 OneID (UUID)。"""
        email = commit.author_email.lower() if commit.author_email else ''
        name = commit.author_name.lower() if commit.author_name else ''
        global_id = None
        if email in self.email_map:
            global_id = self.email_map[email]
        elif name in self.username_map:
            global_id = self.username_map[name]
        elif name in self.name_map:
            global_id = self.name_map[name]
        elif email and '@' in email:
            prefix = email.split('@')[0]
            if prefix in self.username_map:
                global_id = self.username_map[prefix]
        if global_id:
            return global_id
        user = IdentityManager.get_or_create_user(self.session, source='gitlab_commit', external_id=commit.author_email, email=commit.author_email, name=commit.author_name)
        return user.global_user_id

class UserResolver:
    """用户解析器，将 gitlab_id 映射到内部用户 OneID。"""

    def __init__(self, session: Session, client: Any):
        '''"""TODO: Add description.

Args:
    self: TODO
    session: TODO
    client: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.session = session
        self.client = client
        self.cache: Dict[int, Any] = {}
        self._load_cache()

    def _load_cache(self):
        """加载现有 GitLab 映射到缓存。"""
        mappings = self.session.query(IdentityMapping).filter_by(source_system='gitlab').all()
        for m in mappings:
            try:
                self.cache[int(m.external_user_id)] = m.global_user_id
            except (ValueError, TypeError):
                continue

    def resolve(self, gitlab_id: int) -> Optional[Any]:
        """解析 GitLab 用户 ID 到内部 OneID。"""
        if gitlab_id in self.cache:
            return self.cache[gitlab_id]
        try:
            user_data = self.client.get_user(gitlab_id)
            user = IdentityManager.get_or_create_user(self.session, source='gitlab', external_id=str(gitlab_id), email=user_data.get('email'), name=user_data.get('name'), employee_id=user_data.get('username'))
            dept_name = user_data.get('skype')
            if dept_name:
                org = self.session.query(Organization).filter_by(org_name=dept_name, is_current=True).first()
                if not org:
                    org = Organization(org_id=dept_name, org_name=dept_name, org_level=2, sync_version=1, is_current=True)
                    self.session.add(org)
                    self.session.flush()
                user.department_id = org.org_id
            self.session.flush()
            self.cache[gitlab_id] = user.global_user_id
            return user.global_user_id
        except Exception as e:
            logger.warning(f'Failed to resolve user {gitlab_id}: {e}')
            return None
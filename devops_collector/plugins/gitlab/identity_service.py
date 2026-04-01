"""GitLab 身份识别与匹配模块 (支持 SCD Type 2)"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from devops_collector.core.identity_manager import IdentityManager
from devops_collector.core.organization_service import OrganizationService
from devops_collector.models import IdentityMapping, Organization


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
        self.email_map = {}
        self.username_map = {}
        self.name_map = {}
        self._build_index()

    def _build_index(self):
        """构建 GitLab 用户身份索引以进行规则匹配。"""
        mappings = self.session.query(IdentityMapping).filter_by(source_system="gitlab").all()
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

    def match(self, commit: Any) -> Any | None:
        """按 4 级规则匹配 Commit 作者到内部用户 OneID (UUID)。"""
        email = commit.author_email.lower() if commit.author_email else ""
        name = commit.author_name.lower() if commit.author_name else ""
        global_id = None
        if email in self.email_map:
            global_id = self.email_map[email]
        elif name in self.username_map:
            global_id = self.username_map[name]
        elif name in self.name_map:
            global_id = self.name_map[name]
        elif email and "@" in email:
            prefix = email.split("@")[0]
            if prefix in self.username_map:
                global_id = self.username_map[prefix]
        if global_id:
            return global_id
        user = IdentityManager.get_or_create_user(
            self.session,
            source="gitlab_commit",
            external_id=commit.author_email,
            email=commit.author_email,
            name=commit.author_name,
        )
        return user.global_user_id if user else None


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
        self.org_service = OrganizationService(session)
        self.cache: dict[int, Any] = {}
        self._load_cache()

    def _load_cache(self):
        """加载现有 GitLab 映射到缓存。"""
        mappings = self.session.query(IdentityMapping).filter_by(source_system="gitlab").all()
        for m in mappings:
            try:
                self.cache[int(m.external_user_id)] = m.global_user_id
            except (ValueError, TypeError):
                continue

    def resolve(self, gitlab_id: int) -> Any | None:
        """解析 GitLab 用户 ID 到内部 OneID。"""
        if gitlab_id in self.cache:
            return self.cache[gitlab_id]
        try:
            user_data = self.client.get_user(gitlab_id)
            user = IdentityManager.get_or_create_user(
                self.session,
                source="gitlab",
                external_id=str(gitlab_id),
                email=user_data.get("email"),
                name=user_data.get("name"),
                employee_id=user_data.get("username"),
            )
            if user:
                dept_name = user_data.get("skype")
                if dept_name:
                    # 使用统一服务进行 Upsert (GitLab 场景通常使用部门名作为唯一标识)
                    org = self.org_service.upsert_organization(
                        org_code=f"gitlab_dept_{dept_name}",
                        org_name=dept_name,
                        org_level=2,
                        source="gitlab_identity"
                    )
                    if org and org.id:
                        user.department_id = org.id
                self.session.flush()
                self.cache[gitlab_id] = user.global_user_id
                return user.global_user_id
            return None
        except Exception as e:
            logger.warning(f"Failed to resolve user {gitlab_id}: {e}")
            return None

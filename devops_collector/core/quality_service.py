"""Quality Core Service.

封装代码质量、安全扫描与架构防腐相关的统一查询层。
"""

from sqlalchemy.orm import Session

from devops_collector.core import security
from devops_collector.models.base_models import User
from devops_collector.models.dependency import DependencyScan
from devops_collector.plugins.gitlab.models import GitLabProject


class QualityService:
    """处理安全扫描报告与质量指标的查询。"""

    def __init__(self, session: Session):
        self.session = session

    def get_scan(self, scan_id: int):
        """按 ID 查询依赖扫描报告。"""
        return self.session.query(DependencyScan).get(scan_id)

    def list_dependency_scans(self, current_user: User):
        """获取 Dependency Check 扫描结果（支持组织隔离）。"""
        query = self.session.query(DependencyScan).join(GitLabProject)

        # 应用安全策略 (RLS)
        if current_user.role != security.ADMIN_ROLE_KEY:
            # 获取用户所属组织范围
            scope_ids = security.get_user_org_scope_ids(self.session, current_user)
            # 仅显示该组织下的项目扫描记录
            query = query.filter(GitLabProject.organization_id.in_(scope_ids))

        return query.all()

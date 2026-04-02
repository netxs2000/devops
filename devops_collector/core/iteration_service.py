"""Iteration Core Service.

封装迭代计划相关的数据库查询逻辑。
"""

from sqlalchemy.orm import Session

from devops_collector.core import security
from devops_collector.models.base_models import User
from devops_collector.plugins.gitlab.models import GitLabMilestone, GitLabProject


class IterationCoreService:
    """处理迭代相关的数据库查询。"""

    def __init__(self, session: Session):
        self.session = session

    def list_projects(self, current_user: User) -> list[dict]:
        """获取所有可用项目列表。"""
        query = self.session.query(GitLabProject)
        query = security.apply_plugin_privacy_filter(self.session, query, GitLabProject, current_user)
        projects = query.all()
        return [{"id": p.id, "name": p.name, "path": p.path_with_namespace} for p in projects]

    def list_milestones(self, project_id: int) -> list[dict]:
        """获取指定项目的里程碑列表。"""
        milestones = (
            self.session.query(GitLabMilestone)
            .filter(GitLabMilestone.project_id == project_id, GitLabMilestone.state == "active")
            .order_by(GitLabMilestone.due_date)
            .all()
        )
        return [{"id": m.id, "title": m.title, "due_date": m.due_date} for m in milestones]

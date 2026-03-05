"""GitLab 数据采集 Worker 模块。"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from devops_collector.models import SyncLog

from .identity_service import IdentityMatcher, UserResolver
from .mixins.asset_mixin import AssetMixin
from .mixins.base_mixin import BaseMixin
from .mixins.commit_mixin import CommitMixin
from .mixins.issue_mixin import IssueMixin
from .mixins.mr_mixin import MergeRequestMixin
from .mixins.pipeline_mixin import PipelineMixin
from .mixins.traceability_mixin import TraceabilityMixin
from .models import GitLabGroup, GitLabProject


logger = logging.getLogger(__name__)


class GitLabWorker(
    BaseWorker, BaseMixin, TraceabilityMixin, CommitMixin, IssueMixin, MergeRequestMixin, PipelineMixin, AssetMixin
):
    """GitLab 数据采集 Worker。

    支持传统 REST API 客户端 (GitLabClient) 和现代 PyAirbyte 客户端 (AirbyteGitLabClient)。
    """

    SCHEMA_VERSION = "1.2"

    def __init__(self, session: Session, client: Any = None, enable_deep_analysis: bool = False):
        """初始化 GitLab Worker。

        Args:
            session (Session): SQLAlchemy 数据库会话。
            client (Any): 客户端实例，若为 None 则根据配置自动选择。
            enable_deep_analysis (bool): 是否开启深度 Diff 分析。
        """
        if client is None:
            raise ValueError("Client must be provided")

        super().__init__(session, client)
        self.enable_deep_analysis = enable_deep_analysis
        self.identity_matcher = IdentityMatcher(session)
        self.user_resolver = UserResolver(session, client)

    def process_task(self, task: dict) -> dict:
        """实现具体的同步逻辑，由 BaseWorker.run_sync 调用。"""
        from datetime import UTC, datetime
        
        project_id = task.get("project_id")
        if not project_id:
            raise ValueError("No project_id provided in task")

        try:
            project = self._sync_project(project_id)
            if not project:
                return {"status": "skipped", "reason": "project_not_found"}
            
            project.sync_status = "SYNCING"
            self.session.commit()

            since = project.last_synced_at.isoformat() if project.last_synced_at else None
            
            # 核心数据同步
            stats = {
                "commits": self._sync_commits(project, since),
                "issues": self._sync_issues(project, since),
                "mrs": self._sync_merge_requests(project, since),
            }

            # 次要数据及关联信息同步 (容错)
            secondary_syncs = [
                ("_sync_pipelines", "pipelines"),
                ("_sync_deployments", "deployments"),
                ("_sync_tags", "tags"),
                ("_sync_branches", "branches"),
                ("_sync_milestones", "milestones"),
                ("_sync_packages", "packages"),
            ]
            for meth_name, label in secondary_syncs:
                try:
                    getattr(self, meth_name)(project)
                except Exception as e:
                    logger.warning(f"Secondary sync failed for {label} in project {project_id}: {e}")

            if self.enable_deep_analysis:
                try:
                    self._sync_wiki_logs(project)
                    self._sync_dependencies(project)
                except Exception as e:
                    logger.warning(f"Deep analysis failed for project {project_id}: {e}")

            self._match_identities(project)
            
            log_msg = f"Synced: {stats['commits']} commits, {stats['issues']} issues, {stats['mrs']} MRs"
            sync_log = SyncLog(project_id=str(project_id), status="SUCCESS", message=log_msg)
            self.session.add(sync_log)

            # 更新项目元状态
            project.sync_status = "SUCCESS"
            project.last_synced_at = datetime.now(UTC)
            self.session.commit()
            
            return stats
        except Exception as e:
            self.session.rollback()
            logger.error(f"GitLab sync task failed for project {project_id}: {e}", exc_info=True)
            try:
                # 尝试标记为 FAILED
                p_failed = self.session.query(GitLabProject).filter_by(id=project_id).first()
                if p_failed:
                    p_failed.sync_status = "FAILED"
                    self.session.add(SyncLog(project_id=str(project_id), status="FAILED", message=str(e)[:500]))
                    self.session.commit()
            except:
                pass
            raise

    def _sync_project(self, project_id: int) -> GitLabProject | None:
        """同步项目元数据并自动维护 Group 关系。"""
        try:
            p_data = self.client.get_project(project_id)
            if not p_data:
                return None
            self.save_to_staging(source="gitlab", entity_type="project", external_id=project_id, payload=p_data)
            namespace_id = p_data.get("namespace", {}).get("id")
            if namespace_id:
                self._ensure_group(namespace_id)

            project = self.session.query(GitLabProject).filter_by(id=project_id).first()
            if not project:
                project = GitLabProject(id=project_id)
                self.session.add(project)
            project.name = p_data.get("name")
            project.path_with_namespace = p_data.get("path_with_namespace")
            project.group_id = namespace_id
            project.raw_data = p_data  # Update raw_data so hybrid properties work
            return project
        except Exception as e:
            logger.error(f"Failed to sync project {project_id}: {e}")
            return None

    def _ensure_group(self, group_id: int) -> None:
        """确保本地存在对应的 Group 记录。"""
        group = self.session.query(GitLabGroup).filter_by(id=group_id).first()
        if not group:
            try:
                g_data = self.client.get_group(group_id)
                group = GitLabGroup(
                    id=g_data["id"],
                    name=g_data["name"],
                    path=g_data["path"],
                    full_path=g_data["full_path"]
                )
                self.session.add(group)
                self.session.flush()
            except Exception as e:
                logger.warning(f"Failed to sync group {group_id}: {e}")

    def _match_identities(self, project: GitLabProject) -> None:
        """匹配项目内未关联用户的提交记录。"""
        from devops_collector.plugins.gitlab.models import GitLabCommit as CommitModel

        unlinked = self.session.query(CommitModel).filter_by(project_id=project.id, gitlab_user_id=None).all()
        for commit in unlinked:
            user_id = self.identity_matcher.match(commit)
            if user_id:
                commit.gitlab_user_id = user_id


PluginRegistry.register_worker("gitlab", GitLabWorker)

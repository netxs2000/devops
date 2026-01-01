"""GitLab 数据采集 Worker 模块。

本模块实现了 GitLabWorker 类，负责协调从 GitLab API 获取数据并存储到数据库的
完整流程。支持项目元数据、提交记录、Issue、合并请求、流水线、部署、Wiki、
依赖及制品库等全量或增量同步。

架构重构说明:
该类已通过 Mixin 模式进行拆分，以解决 God Class 问题。
- BaseMixin: 通用批处理
- CommitMixin: 提交记录
- IssueMixin: Issue 
- MergeRequestMixin: MR
- PipelineMixin: 流水线和部署
- AssetMixin: 其他资产 (Tag, Branch, Milestone, Package, Wiki, Dependency)
- TraceabilityMixin: 链路追溯

Typical Usage:
    worker = GitLabWorker(session, client)
    worker.process_task({"project_id": 123})
"""
import logging
from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from devops_collector.core.utils import parse_iso8601
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.gitlab.models import Project, GitLabGroup, SyncLog
from devops_collector.core.identity_manager import IdentityManager
from devops_collector.plugins.gitlab.identity import IdentityMatcher

# Mixins
from devops_collector.plugins.gitlab.mixins.base_mixin import BaseMixin
from devops_collector.plugins.gitlab.mixins.traceability_mixin import TraceabilityMixin
from devops_collector.plugins.gitlab.mixins.commit_mixin import CommitMixin
from devops_collector.plugins.gitlab.mixins.issue_mixin import IssueMixin
from devops_collector.plugins.gitlab.mixins.mr_mixin import MergeRequestMixin
from devops_collector.plugins.gitlab.mixins.pipeline_mixin import PipelineMixin
from devops_collector.plugins.gitlab.mixins.asset_mixin import AssetMixin

logger = logging.getLogger(__name__)


class GitLabWorker(BaseWorker, BaseMixin, TraceabilityMixin, CommitMixin, 
                   IssueMixin, MergeRequestMixin, PipelineMixin, AssetMixin):
    """GitLab 数据采集 Worker。
    
    负责具体项目的全生命周期数据同步，包括基础信息、研发活动、协作行为以及效能指标。
    
    Attributes:
        session (Session): 数据库会话。
        client (GitLabClient): GitLab API 客户端。
        enable_deep_analysis (bool): 是否启用深度分析（如代码 Diff 分析，计算量较大）。
        identity_manager (IdentityManager): 身份映射管理器。
    """
    SCHEMA_VERSION = "1.1" # GitLab API 结构版本

    def __init__(self, session: Session, client: GitLabClient, enable_deep_analysis: bool = False):
        """初始化 GitLab Worker。
        
        Args:
            session (Session): SQLAlchemy 会话。
            client (GitLabClient): GitLab 客户端实例。
            enable_deep_analysis (bool): 是否执行深度分析。默认为 False。
        """
        super().__init__(session, client)
        self.enable_deep_analysis = enable_deep_analysis
        self.identity_matcher = IdentityMatcher(session)
        self.user_resolver = UserResolver(session, client)
    
    def process_task(self, task: dict):
        """处理 GitLab 同步任务。
        
        根据任务配置同步单个项目的所有维度数据，并记录同步日志。
        
        Args:
            task (dict): 任务配置，需包含 'project_id'。
                示例: {"project_id": 456}
                
        Returns:
            None
            
        Raises:
            Exception: 同步过程中遇到未捕获的错误。
        """
        project_id = task.get('project_id')
        if not project_id:
            logger.error("No project_id provided in task")
            return

        try:
            # 1. 同步项目基础信息
            project = self._sync_project(project_id)
            if not project:
                return

            since = project.last_synced_at.isoformat() if project.last_synced_at else None
            
            # 2. 同步各类资源 (顺序敏感，部分资源依赖 Project 存在)
            # 统计计数用于日志
            commits_count = self._sync_commits(project, since)
            issues_count = self._sync_issues(project, since)
            mrs_count = self._sync_merge_requests(project, since)
            self._sync_pipelines(project) # 流水线暂不支持简单 since 过滤，通常依赖 IID 增量
            self._sync_deployments(project)
            self._sync_tags(project)
            self._sync_branches(project)
            self._sync_milestones(project)
            self._sync_packages(project)
            
            # 3. 深度分析 (CALMS Sharing & Automation)
            if self.enable_deep_analysis:
                try:
                    self._sync_wiki_logs(project)
                    self._sync_dependencies(project)
                except Exception as e:
                    logger.warning(f"Deep analysis failed for project {project_id}: {e}")
            
            # 3. 身份匹配与后处理
            self._match_identities(project)
            
            project.last_synced_at = datetime.now()
            project.sync_status = 'SUCCESS'
            self.session.commit()
            
            log = SyncLog(
                project_id=project_id,
                status='SUCCESS',
                message=f"Synced: {commits_count} commits, {issues_count} issues, {mrs_count} MRs"
            )
            self.session.add(log)
            self.session.commit()
            
            self.log_success(f"GitLab project {project.name} synced successfully")
            
        except Exception as e:
            self.session.rollback()
            try:
                project = self.session.query(Project).filter_by(id=project_id).first()
                if project:
                    project.sync_status = 'FAILED'
                    self.session.commit()
                    
                log = SyncLog(project_id=project_id, status='FAILED', message=str(e))
                self.session.add(log)
                self.session.commit()
            except:
                pass
            
            self.log_failure(f"Failed to sync GitLab project {project_id}", e)
            raise
    
    def _sync_project(self, project_id: int) -> Optional[Project]:
        """同步项目元数据。
        
        从 GitLab API 获取项目详情，并更新或创建本地 Project 记录及关联的 Group。
        
        Args:
            project_id (int): GitLab 项目的唯一标识 ID。
            
        Returns:
            Optional[Project]: 同步成功的 Project 实体对象，若失败则返回 None。
        """
        try:
            p_data = self.client.get_project(project_id)
            # 演示：将原始项目数据落盘到 Staging 层
            self.save_to_staging(
                source='gitlab',
                entity_type='project',
                external_id=project_id,
                payload=p_data,
                schema_version=self.SCHEMA_VERSION
            )
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None
            
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            if not p_data.get('namespace', {}).get('id'):
                logger.error(f"Project {project_id} has no namespace info")
                return None
            
            # 确保 Group 存在 (简单处理，只建一级)
            group_id = p_data['namespace']['id']
            group = self.session.query(GitLabGroup).filter_by(id=group_id).first()
            if not group:
                try:
                    g_data = self.client.get_group(group_id)
                    group = GitLabGroup(
                        id=g_data['id'],
                        name=g_data['name'],
                        path=g_data['path'],
                        full_path=g_data['full_path'],
                        description=g_data.get('description'),
                        visibility=g_data.get('visibility'),
                        web_url=g_data.get('web_url'),
                        created_at=parse_iso8601(g_data.get('created_at'))
                    )
                    self.session.add(group)
                    self.session.flush()
                except Exception as e:
                    logger.warning(f"Failed to sync group {group_id}: {e}")
            
            project = Project(id=project_id)
            self.session.add(project)
        
        project.name = p_data.get('name')
        project.path_with_namespace = p_data.get('path_with_namespace')
        project.description = p_data.get('description')
        project.web_url = p_data.get('web_url')
        project.default_branch = p_data.get('default_branch')
        project.group_id = p_data.get('namespace', {}).get('id')
        project.star_count = p_data.get('star_count', 0)
        project.forks_count = p_data.get('forks_count', 0)
        project.visibility = p_data.get('visibility')
        project.archived = p_data.get('archived')
        
        stats = p_data.get('statistics', {})
        project.storage_size = stats.get('storage_size')
        project.commit_count = stats.get('commit_count')
        
        project.created_at = parse_iso8601(p_data.get('created_at'))
            
        return project


    def _match_identities(self, project: Project) -> None:
        """匹配项目内未关联用户的提交记录。"""
        
        # 此处简单实现，实际可优化为批量处理
        # 为避免循环依赖问题，Commit 已在 CommitMixin 中处理了同步
        # 这里主要处理那些 gitlab_user_id 为空的 Commit
        # 需引入 Commit 模型，但为了解耦，我们尽量减少此处对 具体 Mixin 内部细节的依赖
        # 但 Commit 是共享模型，所以 query 是安全的
        from devops_collector.plugins.gitlab.models import Commit as CommitModel
        
        unlinked = self.session.query(CommitModel).filter_by(
            project_id=project.id, 
            gitlab_user_id=None
        ).all()
        
        for commit in unlinked:
            user_id = self.identity_matcher.match(commit)
            if user_id:
                commit.gitlab_user_id = user_id
        
        self.session.commit()

PluginRegistry.register_worker('gitlab', GitLabWorker)

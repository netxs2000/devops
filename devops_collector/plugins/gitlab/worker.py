"""GitLab 数据采集 Worker 模块。

本模块实现了 GitLabWorker 类，负责协调从 GitLab API 获取数据并存储到数据库的
完整流程。支持项目元数据、提交记录、Issue、合并请求、流水线、部署、Wiki、
依赖及制品库等全量或增量同步。

Typical Usage:
    worker = GitLabWorker(session, client)
    worker.process_task({"project_id": 123})
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from devops_collector.core.base_worker import BaseWorker
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.gitlab.models import (
    Project, Commit, Issue, MergeRequest, Pipeline, Tag, 
    Branch, Milestone, GitLabPackage, GitLabPackageFile, Note,
    Deployment, CommitFileStats, GitLabWikiLog, GitLabDependency, SyncLog
)
from devops_collector.core.identity_manager import IdentityManager

logger = logging.getLogger(__name__)


from .analyzer import DiffAnalyzer
from .identity import IdentityMatcher, UserResolver


class GitLabWorker(BaseWorker):
    """GitLab 数据采集 Worker。
    
    负责具体项目的全生命周期数据同步，包括基础信息、研发活动、协作行为以及效能指标。
    
    Attributes:
        session (Session): 数据库会话。
        client (GitLabClient): GitLab API 客户端。
        enable_deep_analysis (bool): 是否启用深度分析（如代码 Diff 分析，计算量较大）。
        identity_manager (IdentityManager): 身份映射管理器。
    """

    def __init__(self, session: Session, client: GitLabClient, enable_deep_analysis: bool = False):
        """初始化 GitLab Worker。
        
        Args:
            session (Session): SQLAlchemy 会话。
            client (GitLabClient): GitLab 客户端实例。
            enable_deep_analysis (bool): 是否执行深度分析。默认为 False。
        """
        super().__init__(session, client)
        self.enable_deep_analysis = enable_deep_analysis
        self.identity_manager = IdentityManager(session)
    
    def process_task(self, task: dict):
        """处理 GitLab 同步任务。
        
        根据任务配置同步单个项目的所有维度数据，并记录同步日志。
        
        Args:
            task (dict): 任务配置，需包含 'project_id'。
                示例: {"project_id": 456, "sync_types": ["commits", "issues"]}
                
        Returns:
            None
            
        Raises:
            Exception: 同步过程中遇到未捕获的错误。
        """
        project_id = task.get('project_id')
        if not project_id:
            logger.error("No project_id provided in task")
            return

        start_time = datetime.now()
        try:
            # 1. 同步项目基础信息
            project = self._sync_project(project_id)
            if not project:
                return

            since = project.last_synced_at.isoformat() if project.last_synced_at else None
            
            # 2. 同步各类资源 (顺序敏感，部分资源依赖 Project 存在)
            self._sync_commits(project, since)
            self._sync_issues(project, since)
            self._sync_merge_requests(project, since)
            self._sync_pipelines(project) # 流水线暂不支持简单 since 过滤，通常依赖 IID 增量
            self._sync_deployments(project)
            self._sync_tags(project)
            self._sync_branches(project)
            self._sync_milestones(project)
            self._sync_packages(project)
            self._sync_wiki_logs(project)
            self._sync_dependencies(project)

            # 3. 身份匹配与后处理
            self._match_identities(project)
            
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
                        created_at=datetime.fromisoformat(g_data['created_at'].replace('Z', '+00:00')) if g_data.get('created_at') else None
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
        
        if p_data.get('created_at'):
            project.created_at = datetime.fromisoformat(p_data['created_at'].replace('Z', '+00:00'))
            
        # 同步 Wiki 日志（CALMS Sharing 维度）
        if self.enable_deep_analysis:
            try:
                self._sync_wiki_logs(project)
                self._sync_dependencies(project)
            except Exception as e:
                logger.warning(f"Failed to sync sharing metadata for project {project_id}: {e}")

        return project

    def _sync_dependencies(self, project: Project) -> None:
        """同步项目的第三方/内部依赖关系。
        
        从 GitLab 依赖列表 API 提取信息，并保存到 GitLabDependency 表中。
        
        Args:
            project (Project): 需要同步依赖的项目实体。
            
        Returns:
            None
        """
        for dep in self.client.get_project_dependencies(project.id):
            # 简单去重：按名称和版本
            existing = self.session.query(GitLabDependency).filter_by(
                project_id=project.id,
                name=dep['name'],
                version=dep['version']
            ).first()
            
            if existing:
                continue
                
            dependency = GitLabDependency(
                project_id=project.id,
                name=dep['name'],
                version=dep['version'],
                package_manager=dep.get('package_manager'),
                dependency_type=dep.get('dependency_type'),
                raw_data=dep
            )
            self.session.add(dependency)

    def _sync_wiki_logs(self, project: Project) -> None:
        """同步 Wiki 事件日志。
        
        基于事件审计 API 采集 Wiki 的创建、更新或删除活动。
        
        Args:
            project (Project): 关联的项目实体。
            
        Returns:
            None
        """
        for event in self.client.get_project_wiki_events(project.id):
            # 检查是否已存在
            existing = self.session.query(GitLabWikiLog).filter_by(
                project_id=project.id,
                created_at=datetime.fromisoformat(event['created_at'].replace('Z', '+00:00'))
            ).first()
            
            if existing:
                continue
                
            wiki_log = GitLabWikiLog(
                project_id=project.id,
                title=event.get('target_title'),
                slug=event.get('target_title'), # 简化处理
                action=event.get('action_name'),
                created_at=datetime.fromisoformat(event['created_at'].replace('Z', '+00:00')),
                raw_data=event
            )
            
            if event.get('author_id') and self.user_resolver:
                wiki_log.user_id = self.user_resolver.resolve(event['author_id'])
                
            self.session.add(wiki_log)

    def _sync_commits(self, project: Project, since: Optional[str]) -> int:
        """同步提交记录。
        
        使用生成器流式同步项目的 Git 提交。
        
        Args:
            project (Project): 项目实体对象。
            since (Optional[str]): ISO 格式的时间字符串，仅同步该时间之后的提交。
            
        Returns:
            int: 本次成功处理的提交总数。
        """
        count = self._process_generator(
            self.client.get_project_commits(project.id, since=since),
            lambda batch: self._save_commits_batch(project, batch)
        )
        return count

    def _save_commits_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存提交记录，并触发追溯与行为分析。
        
        Args:
            project (Project): 关联的项目实体。
            batch (List[dict]): 从 API 获取的原始提交数据列表。
            
        Returns:
            None
        """
        existing = self.session.query(Commit.id).filter(
            Commit.project_id == project.id,
            Commit.id.in_([c['id'] for c in batch])
        ).all()
        existing_ids = {c.id for c in existing}
        
        new_commits = []
        for data in batch:
            if data['id'] in existing_ids:
                continue
            
            commit = Commit(
                id=data['id'],
                project_id=project.id,
                short_id=data['short_id'],
                title=data['title'],
                author_name=data['author_name'],
                author_email=data['author_email'],
                message=data['message'],
                authored_date=datetime.fromisoformat(data['authored_date'].replace('Z', '+00:00')),
                committed_date=datetime.fromisoformat(data['committed_date'].replace('Z', '+00:00'))
            )
            
            stats = data.get('stats', {})
            commit.additions = stats.get('additions', 0)
            commit.deletions = stats.get('deletions', 0)
            commit.total = stats.get('total', 0)
            
            self.session.add(commit)
            new_commits.append(commit)
            
            # 自动化链路追踪提取
            self._apply_traceability_extraction(commit)
            
            # 行为特征：加班识别与行为特征
            self._apply_commit_behavior_analysis(commit)
        
        if self.enable_deep_analysis and new_commits:
            for commit in new_commits:
                self._process_commit_diffs(project, commit)

    def _process_commit_diffs(self, project: Project, commit: Commit) -> None:
        """分析 Commit 的 Diff 并分类统计文件变更。
        
        提取每次提交中具体文件的代码、注释和空行变更数量，并识别文件所属的技术栈。
        
        Args:
            project (Project): 项目实体。
            commit (Commit): 需要分析 Diff 的提交实体。
            
        Returns:
            None
        """
        try:
            diffs = self.client.get_commit_diff(project.id, commit.id)
            for diff in diffs:
                file_path = diff.get('new_path') or diff.get('old_path')
                if not file_path or DiffAnalyzer.is_ignored(file_path):
                    continue
                
                # 分析差异统计
                diff_text = diff.get('diff', '')
                stats = DiffAnalyzer.analyze_diff(diff_text, file_path)
                
                # 识别文件分类
                category = DiffAnalyzer.get_file_category(file_path)
                
                # 保存统计
                file_stats = CommitFileStats(
                    commit_id=commit.id,
                    file_path=file_path,
                    file_type_category=category,
                    **stats
                )
                self.session.add(file_stats)
        except Exception as e:
            logger.warning(f"Failed to analyze diff for commit {commit.id}: {e}")

    def _sync_issues(self, project: Project, since: Optional[str]) -> int:
        """从项目同步 Issue。
        
        Args:
            project (Project): 关联的项目实体。
            since (Optional[str]): ISO 格式时间，仅同步该时间后的 Issue。
            
        Returns:
            int: 处理的 Issue 总数。
        """
        count = self._process_generator(
            self.client.get_project_issues(project.id, since=since),
            lambda batch: self._save_issues_batch(project, batch)
        )
        return count

    def _save_issues_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存 Issue 元数据。
        
        Args:
            project (Project): 关联的项目实体。
            batch (List[dict]): Issue 原始数据列表。
            
        Returns:
            None
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(Issue).filter(Issue.id.in_(ids)).all()
        existing_map = {i.id: i for i in existing}
        
        for data in batch:
            issue = existing_map.get(data['id'])
            if not issue:
                issue = Issue(id=data['id'])
                self.session.add(issue)
            
            issue.project_id = project.id
            issue.iid = data['iid']
            issue.title = data['title']
            issue.description = data.get('description')
            issue.state = data['state']
            issue.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            issue.updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
            
            if data.get('closed_at'):
                issue.closed_at = datetime.fromisoformat(data['closed_at'].replace('Z', '+00:00'))
                
            time_stats = data.get('time_stats', {})
            issue.time_estimate = time_stats.get('time_estimate')
            issue.total_time_spent = time_stats.get('total_time_spent')
            
            issue.labels = data.get('labels', [])
            
            if data.get('author'):
                if self.user_resolver:
                    uid = self.user_resolver.resolve(data['author']['id'])
                    issue.author_id = uid
            
            # 如果开启了深度分析，则同步 Issue 事件历史（CALMS 文化扫描）
            if self.enable_deep_analysis:
                self._sync_issue_events(project, data)

    def _sync_issue_events(self, project: Project, issue_data: Dict) -> None:
        """同步单个 Issue 的所有资源事件（状态、标签、里程碑）。
        
        用于 CALMS 模型中文化与协作维度的扫描。
        
        Args:
            project (Project): 关联的项目。
            issue_data (Dict): Issue 的原始数据。
            
        Returns:
            None
        """
        project_id = project.id
        issue_iid = issue_data['iid']
        issue_id = issue_data['id']
        
        # 1. 同步状态变更事件
        for event in self.client.get_issue_state_events(project_id, issue_iid):
            self._save_issue_event(issue_id, 'state', event)
            
        # 2. 同步标签变更事件
        for event in self.client.get_issue_label_events(project_id, issue_iid):
            self._save_issue_event(issue_id, 'label', event)
            
        # 3. 同步里程碑变更事件
        for event in self.client.get_issue_milestone_events(project_id, issue_iid):
            self._save_issue_event(issue_id, 'milestone', event)

    def _save_issue_event(self, issue_id: int, event_type: str, data: Dict) -> None:
        """保存 Issue 事件，确保幂等。
        
        Args:
            issue_id (int): 数据库内 Issue 的 ID。
            event_type (str): 事件类型 (state, label, milestone)。
            data (Dict): 事件原始 JSON 内容。
            
        Returns:
            None
        """
        external_id = data['id']
        
        # 检查是否已存在
        existing = self.session.query(GitLabIssueEvent).filter_by(
            issue_id=issue_id, 
            event_type=event_type, 
            external_event_id=external_id
        ).first()
        
        if existing:
            return
            
        event = GitLabIssueEvent(
            issue_id=issue_id,
            event_type=event_type,
            external_event_id=external_id,
            action=data.get('state') or data.get('action') or 'update',
            created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
            meta_info=data
        )
        
        # 关联用户
        if data.get('user') and self.user_resolver:
            event.user_id = self.user_resolver.resolve(data['user']['id'])
            
        self.session.add(event)

    def _sync_merge_requests(self, project: Project, since: Optional[str]) -> int:
        """从项目同步合并请求 (MR)。
        
        Args:
            project (Project): 项目实体。
            since (Optional[str]): 增量同步起始时间。
            
        Returns:
            int: 处理的 MR 数量。
        """
        return self._process_generator(
            self.client.get_project_merge_requests(project.id, since=since),
            lambda batch: self._save_mrs_batch(project, batch)
        )

    def _save_mrs_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存合并请求记录。
        
        Args:
            project (Project): 关联项目。
            batch (List[dict]): MR 原始数据列表。
            
        Returns:
            None
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(MergeRequest).filter(MergeRequest.id.in_(ids)).all()
        existing_map = {m.id: m for m in existing}
        
        for data in batch:
            mr = existing_map.get(data['id'])
            if not mr:
                mr = MergeRequest(id=data['id'])
                self.session.add(mr)
            
            mr.project_id = project.id
            mr.iid = data['iid']
            mr.title = data['title']
            mr.description = data.get('description')
            mr.state = data['state']
            mr.author_username = data.get('author', {}).get('username')
            mr.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            mr.updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
            mr.merge_commit_sha = data.get('merge_commit_sha')
            
            if data.get('merged_at'):
                mr.merged_at = datetime.fromisoformat(data['merged_at'].replace('Z', '+00:00'))
            if data.get('closed_at'):
                mr.closed_at = datetime.fromisoformat(data['closed_at'].replace('Z', '+00:00'))
                
            if data.get('author'):
                if self.user_resolver:
                    uid = self.user_resolver.resolve(data['author']['id'])
                    mr.author_id = uid
            
            # 自动化链路追踪提取
            self._apply_traceability_extraction(mr)
            
            # 行为特征：协作深度与评审质量 (仅对已合并或已进入评审的 MR)
            if self.enable_deep_analysis or mr.state in ('merged', 'opened'):
                self._apply_mr_collaboration_analysis(project, mr)

    def _sync_pipelines(self, project: Project) -> int:
        """从项目同步流水线记录。
        
        Args:
            project (Project): 项目实体。
            
        Returns:
            int: 同步成功的流水线总数。
        """
        return self._process_generator(
            self.client.get_project_pipelines(project.id),
            lambda batch: self._save_pipelines_batch(project, batch)
        )

    def _save_pipelines_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存流水线及其基本指标。
        
        Args:
            project (Project): 关联项目。
            batch (List[dict]): 流水线数据列表。
            
        Returns:
            None
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(Pipeline).filter(Pipeline.id.in_(ids)).all()
        existing_map = {p.id: p for p in existing}
        
        for data in batch:
            p = existing_map.get(data['id'])
            if not p:
                p = Pipeline(id=data['id'])
                self.session.add(p)
            
            p.project_id = project.id
            p.status = data['status']
            p.ref = data.get('ref')
            p.sha = data.get('sha')
            p.source = data.get('source')
            p.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            p.updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
            p.coverage = data.get('coverage')

    def _sync_deployments(self, project: Project) -> int:
        """同步部署记录。
        
        Args:
            project (Project): 项目实体。
            
        Returns:
            int: 部署记录总数。
        """
        return self._process_generator(
            self.client.get_project_deployments(project.id),
            lambda batch: self._save_deployments_batch(project, batch)
        )
    
    def _save_deployments_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存部署信息。
        
        Args:
            project (Project): 关联项目。
            batch (List[dict]): 部署原始数据。
            
        Returns:
            None
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(Deployment).filter(Deployment.id.in_(ids)).all()
        existing_map = {d.id: d for d in existing}
        
        for data in batch:
            d = existing_map.get(data['id'])
            if not d:
                d = Deployment(id=data['id'])
                self.session.add(d)
                
            d.project_id = project.id
            d.iid = data['iid']
            d.status = data['status']
            d.environment = data.get('environment', {}).get('name')
            d.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            d.updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
            d.ref = data.get('ref')
            d.sha = data.get('sha')
    
    def _sync_tags(self, project: Project) -> int:
        """同步 Git 标签。
        
        Args:
            project (Project): 项目实体。
            
        Returns:
            int: 标签总数。
        """
        count = self._process_generator(
            self.client.get_project_tags(project.id),
            lambda batch: self._save_tags_batch(project, batch)
        )
        project.tags_count = count
        return count

    def _save_tags_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存标签。
        
        Args:
            project (Project): 关联项目。
            batch (List[dict]): 标签原始数据。
            
        Returns:
            None
        """
        names = [item['name'] for item in batch]
        existing = self.session.query(Tag).filter(
            Tag.project_id == project.id,
            Tag.name.in_(names)
        ).all()
        existing_map = {t.name: t for t in existing}
        
        for data in batch:
            tag = existing_map.get(data['name'])
            if not tag:
                tag = Tag(project_id=project.id, name=data['name'])
                self.session.add(tag)
            
            tag.message = data.get('message')
            tag.commit_sha = data.get('commit', {}).get('id')
    
    def _sync_branches(self, project: Project) -> int:
        """同步分支元数据。
        
        Args:
            project (Project): 项目实体。
            
        Returns:
            int: 分支总数。
        """
        return self._process_generator(
            self.client.get_project_branches(project.id),
            lambda batch: self._save_branches_batch(project, batch)
        )

    def _save_branches_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存分支。
        
        Args:
            project (Project): 关联项目。
            batch (List[dict]): 分支数据列表。
            
        Returns:
            None
        """
        names = [item['name'] for item in batch]
        existing = self.session.query(Branch).filter(
            Branch.project_id == project.id,
            Branch.name.in_(names)
        ).all()
        existing_map = {b.name: b for b in existing}
        
        for data in batch:
            branch = existing_map.get(data['name'])
            if not branch:
                branch = Branch(project_id=project.id, name=data['name'])
                self.session.add(branch)
            
            commit_info = data.get('commit', {})
            branch.last_commit_sha = commit_info.get('id')
            branch.last_committer_name = commit_info.get('committer_name')
            branch.is_merged = data.get('merged', False)
            branch.is_protected = data.get('protected', False)
            branch.is_default = data.get('default', False)
            
            if commit_info.get('committed_date'):
                try:
                    branch.last_commit_date = datetime.fromisoformat(
                        commit_info['committed_date'].replace('Z', '+00:00')
                    )
                except:
                    pass
    
    def _sync_milestones(self, project: Project) -> int:
        """同步里程碑 (支持流式处理)。
        
        Args:
            project (Project): 项目实体。
            
        Returns:
            int: 里程碑总数。
        """
        return self._process_generator(
            self.client.get_project_milestones(project.id),
            lambda batch: self._save_milestones_batch(project, batch)
        )

    def _save_milestones_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存里程碑。
        
        Args:
            project (Project): 关联项目。
            batch (List[dict]): 里程碑数据列表。
            
        Returns:
            None
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(Milestone).filter(Milestone.id.in_(ids)).all()
        existing_map = {m.id: m for m in existing}
        
        for data in batch:
            ms = existing_map.get(data['id'])
            if not ms:
                ms = Milestone(id=data['id'])
                self.session.add(ms)
            
            ms.project_id = project.id
            ms.iid = data.get('iid')
            ms.title = data.get('title')
            ms.description = data.get('description')
            ms.state = data.get('state')
            
            if data.get('due_date'):
                 # due_date 通常是 YYYY-MM-DD
                try:
                    ms.due_date = datetime.fromisoformat(data['due_date']).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
                    
            if data.get('start_date'):
                try:
                    ms.start_date = datetime.fromisoformat(data['start_date']).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
                    
            if data.get('created_at'):
                 ms.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            if data.get('updated_at'):
                 ms.updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))

    def _sync_packages(self, project: Project) -> int:
        """同步项目的制品包。
        
        Args:
            project (Project): 项目实体。
            
        Returns:
            int: 制品包总数。
        """
        return self._process_generator(
            self.client.get_packages(project.id),
            lambda batch: self._save_packages_batch(project, batch)
        )

    def _save_packages_batch(self, project: Project, batch: List[dict]) -> None:
        """保存包及其关联文件。
        
        Args:
            project (Project): 关联项目。
            batch (List[dict]): 包数据列表。
            
        Returns:
            None
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(GitLabPackage).filter(GitLabPackage.id.in_(ids)).all()
        existing_map = {p.id: p for p in existing}
        
        for data in batch:
            pkg = existing_map.get(data['id'])
            if not pkg:
                pkg = GitLabPackage(id=data['id'])
                self.session.add(pkg)
            
            pkg.project_id = project.id
            pkg.name = data['name']
            pkg.version = data.get('version')
            pkg.package_type = data.get('package_type')
            pkg.status = data.get('status')
            pkg.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
            pkg.web_url = data.get('_links', {}).get('web_path')
            pkg.raw_data = data
            
            # 同步包文件 (相对较少，直接处理)
            try:
                files_data = self.client.get_package_files(project.id, pkg.id)
                self._sync_package_files(pkg, files_data)
            except Exception as e:
                logger.warning(f"Failed to sync files for package {pkg.id}: {e}")

    def _sync_package_files(self, package: GitLabPackage, files_data: List[dict]) -> None:
        """同步特定包下的文件。
        
        Args:
            package (GitLabPackage): 数据库内的包实体。
            files_data (List[dict]): 文件原始数据。
            
        Returns:
            None
        """
        ids = [f['id'] for f in files_data]
        existing = {f.id for f in package.files}
        
        for f_data in files_data:
            if f_data['id'] in existing:
                continue
            
            f_obj = GitLabPackageFile(
                id=f_data['id'],
                package_id=package.id,
                file_name=f_data['file_name'],
                size=f_data.get('size'),
                file_sha1=f_data.get('file_sha1'),
                file_sha256=f_data.get('file_sha256'),
                created_at=datetime.fromisoformat(f_data['created_at'].replace('Z', '+00:00')),
                raw_data=f_data
            )
            self.session.add(f_obj)

    def _match_identities(self, project: Project) -> None:
        """匹配项目内未关联用户的提交记录。
        
        Args:
            project (Project): 项目实体。
            
        Returns:
            None
        """
        if not self.identity_matcher:
            self.identity_matcher = IdentityMatcher(self.session)
        
        unlinked = self.session.query(Commit).filter_by(
            project_id=project.id, 
            gitlab_user_id=None
        ).all()
        
        for commit in unlinked:
            user_id = self.identity_matcher.match(commit)
            if user_id:
                commit.gitlab_user_id = user_id
        
        self.session.commit()
    
    def _apply_traceability_extraction(self, obj: Any) -> None:
        """从项目对象（Commit/MR）的文本内容中提取业务需求追溯信息。
        
        支持正则匹配:
        - Jira: [A-Z]+-\d+ (如 PROJ-123)
        - ZenTao: #\d+ (如 #456)
        
        Args:
            obj (Any): 提交记录 (Commit) 或合并请求 (MergeRequest) 实体。
            
        Returns:
            None
        """
        text_to_scan = ""
        if isinstance(obj, Commit):
            text_to_scan = f"{obj.title}\n{obj.message}"
        elif isinstance(obj, MergeRequest):
            text_to_scan = f"{obj.title}\n{obj.description or ''}"
        
        if not text_to_scan:
            return

        # 1. 匹配 Jira (大写字母+横线+数字)
        jira_matches = list(set(re.findall(r'([A-Z]{2,}-\d+)', text_to_scan)))
        # 2. 匹配 ZenTao (井号+数字)
        zentao_matches = list(set(re.findall(r'#(\d+)', text_to_scan)))

        # 更新对象字段并建立 TraceabilityLink
        if jira_matches:
            self._save_traceability_results(obj, jira_matches, 'jira')
        
        if zentao_matches:
            self._save_traceability_results(obj, zentao_matches, 'zentao')

    def _save_traceability_results(self, obj: Any, ids: List[str], source: str) -> None:
        """保存提取到的追溯 ID 到对象并创建映射表记录。
        
        Args:
            obj (Any): 目标实体对象。
            ids (List[str]): 提取到的外部 ID 列表。
            source (str): 来源系统类型 (jira, zentao)。
            
        Returns:
            None
        """
        if isinstance(obj, MergeRequest):
            # MR 通常只关联一个主需求，取第一个
            obj.external_issue_id = ids[0]
            obj.issue_source = source
        elif isinstance(obj, Commit):
            # Commit 支持关联多个需求
            if not obj.linked_issue_ids:
                obj.linked_issue_ids = []
            
            # 合并并去重
            current_ids = set(obj.linked_issue_ids)
            current_ids.update(ids)
            obj.linked_issue_ids = list(current_ids)
            obj.issue_source = source

        # 创建通用追溯链路记录
        target_type = 'commit' if isinstance(obj, Commit) else 'mr'
        target_id = obj.id if isinstance(obj, Commit) else str(obj.iid)

        for ext_id in ids:
            # 幂等检查：防止重复插入链路记录
            existing = self.session.query(TraceabilityLink).filter_by(
                source_system=source,
                source_id=ext_id,
                target_system='gitlab',
                target_type=target_type,
                target_id=target_id
            ).first()

            if not existing:
                link = TraceabilityLink(
                    source_system=source,
                    source_type='task' if source == 'zentao' else 'issue',
                    source_id=ext_id,
                    target_system='gitlab',
                    target_type=target_type,
                    target_id=target_id,
                    link_type='fixes',
                    raw_data={'auto_extracted': True, 'found_in': text_to_scan[:200] if 'text_to_scan' in locals() else None}
                )
                self.session.add(link)

    def _apply_commit_behavior_analysis(self, commit: Commit) -> None:
        """分析 Commit 的行为特征（如加班识别）。
        
        Args:
            commit (Commit): 提交实体。
            
        Returns:
            None
        """
        if not commit.committed_date:
            return
            
        dt = commit.committed_date
        # 加班定义：周末，或常规工作时间 (09:00 - 19:00) 之外 (取 20:00 - 08:00)
        is_weekend = dt.weekday() >= 5
        is_night = dt.hour >= 20 or dt.hour < 8
        
        commit.is_off_hours = is_weekend or is_night

    def _apply_mr_collaboration_analysis(self, project: Project, mr: MergeRequest) -> None:
        """分析合并请求的协作深度与评审质量。
        
        Args:
            project (Project): 关联项目。
            mr (MergeRequest): 合并请求实体。
            
        Returns:
            None
        """
        try:
            # 1. 获取审批数
            approvals = self.client.get_mr_approvals(project.id, mr.iid)
            mr.approval_count = len(approvals.get('approved_by', []))
            
            # 2. 获取评论与首次响应
            notes = list(self.client.get_mr_notes(project.id, mr.iid))
            human_notes = [n for n in notes if n.get('system') is False]
            mr.human_comment_count = len(human_notes)
            
            if human_notes:
                # 按创建时间排序
                human_notes.sort(key=lambda x: x['created_at'])
                first_note_at = datetime.fromisoformat(human_notes[0]['created_at'].replace('Z', '+00:00'))
                mr.first_response_at = first_note_at
            
            # 3. 计算评审周期 (以系统通知中提到 "added ... commits" 的次数为近似值)
            system_notes = [n for n in notes if n.get('system') is True]
            # 每一波新提交通常对应一次代码打回后的修订
            updated_commits_notes = [n for n in system_notes if "added" in n.get('body', "").lower() and "commit" in n.get('body', "").lower()]
            mr.review_cycles = 1 + len(updated_commits_notes)
            
            # 4. 计算评审耗时
            if mr.merged_at and mr.created_at:
                delta = mr.merged_at - mr.created_at
                mr.review_time_total = int(delta.total_seconds())
                
            # 5. 质量门禁状态 (基于关联流水线记录)
            pipelines = self.client.get_mr_pipelines(project.id, mr.iid)
            if pipelines:
                latest_p = pipelines[0] # 通常是按倒序排列的
                mr.quality_gate_status = 'passed' if latest_p.get('status') == 'success' else 'failed'

        except Exception as e:
            logger.warning(f"Failed to analyze MR collaboration for {mr.iid}: {e}")

    def _process_generator(self, generator, processor_func, batch_size: int = 500) -> int:
        """通用的生成器批处理助手。
        
        Args:
            generator: GitLab API 返回的生成器对象。
            processor_func: 用于处理单批次数据的回调函数。
            batch_size (int): 每批次处理的数据量，默认 500。
            
        Returns:
            int: 总处理记录数。
        """
        count = 0
        batch = []
        for item in generator:
            batch.append(item)
            if len(batch) >= batch_size:
                try:
                    processor_func(batch)
                    self.session.commit()
                    count += len(batch)
                except Exception as e:
                    self.session.rollback()
                    logger.error(f"Batch processing failed: {e}")
                    raise
                finally:
                    batch = []
        
        if batch:
            try:
                processor_func(batch)
                self.session.commit()
                count += len(batch)
            except Exception as e:
                self.session.rollback()
                logger.error(f"Final batch processing failed: {e}")
                raise
                
        return count


PluginRegistry.register_worker('gitlab', GitLabWorker)

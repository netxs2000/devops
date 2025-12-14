"""GitLab 数据采集 Worker

基于 BaseWorker 实现的 GitLab 数据同步逻辑。
复用原有 worker.py 中的辅助类 (DiffAnalyzer, IdentityMatcher, OrgManager, UserResolver)。
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from .client import GitLabClient

# 使用统一的模型架构
from devops_collector.models import (
    Project, Commit, Issue, MergeRequest, Pipeline, 
    Deployment, Note, Tag, Branch, User, Organization,
    CommitFileStats, SyncLog
)

logger = logging.getLogger(__name__)


class DiffAnalyzer:
    """代码差异分析器，将 Git diff 拆分为代码/注释/空行三类。"""
    
    COMMENT_SYMBOLS = {
        # 井号注释
        'py': '#', 'rb': '#', 'sh': '#', 'yaml': '#', 'yml': '#', 
        'dockerfile': '#', 'pl': '#', 'r': '#',
        # 双斜杠注释
        'java': '//', 'js': '//', 'ts': '//', 'c': '//', 'cpp': '//', 
        'cs': '//', 'go': '//', 'rs': '//', 'swift': '//', 'kt': '//', 
        'scala': '//', 'php': '//',
        # 其他
        'html': '<!--', 'xml': '<!--',
        'css': '/*', 'scss': '/*', 'less': '/*',
        'sql': '--',
    }
    
    IGNORED_PATTERNS = [
        '*.lock', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        '*.min.js', '*.min.css', '*.map',
        'node_modules/*', 'dist/*', 'build/*', 'vendor/*',
        '*.svg', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico',
        '*.pdf', '*.exe', '*.dll', '*.so', '*.dylib',
    ]
    
    @classmethod
    def is_ignored(cls, file_path: str) -> bool:
        """检查文件是否应被忽略。"""
        import fnmatch
        for pattern in cls.IGNORED_PATTERNS:
            if fnmatch.fnmatch(file_path.lower(), pattern):
                return True
        return False
    
    @classmethod
    def get_comment_symbol(cls, file_path: str) -> Optional[str]:
        """根据文件扩展名获取注释符号。"""
        ext = file_path.split('.')[-1].lower() if '.' in file_path else ''
        return cls.COMMENT_SYMBOLS.get(ext)
    
    @classmethod
    def analyze_diff(cls, diff_text: str, file_path: str) -> Dict[str, int]:
        """分析 Git diff 文本，返回分类统计。"""
        stats = {
            'code_added': 0, 'code_deleted': 0,
            'comment_added': 0, 'comment_deleted': 0,
            'blank_added': 0, 'blank_deleted': 0
        }
        
        symbol = cls.get_comment_symbol(file_path)
        
        for line in diff_text.split('\n'):
            if line.startswith('@@') or line.startswith('+++') or line.startswith('---'):
                continue
            
            if len(line) < 1:
                continue
                
            content = line[1:].strip()
            is_blank = (content == '')
            is_comment = symbol and content.startswith(symbol)
            
            if line.startswith('+'):
                if is_blank:
                    stats['blank_added'] += 1
                elif is_comment:
                    stats['comment_added'] += 1
                else:
                    stats['code_added'] += 1
            elif line.startswith('-'):
                if is_blank:
                    stats['blank_deleted'] += 1
                elif is_comment:
                    stats['comment_deleted'] += 1
                else:
                    stats['code_deleted'] += 1
                    
        return stats


class IdentityMatcher:
    """身份匹配器，将 Commit 作者信息关联到 GitLab 用户。"""
    
    def __init__(self, session: Session):
        self.session = session
        self._build_index()
    
    def _build_index(self):
        """构建用户索引以提高匹配性能。"""
        users = self.session.query(User).all()
        self.email_map = {}
        self.username_map = {}
        self.name_map = {}
        
        for u in users:
            if u.email:
                self.email_map[u.email.lower()] = u
            if u.public_email:
                self.email_map[u.public_email.lower()] = u
            if u.username:
                self.username_map[u.username.lower()] = u
            if u.name:
                self.name_map[u.name.lower()] = u
    
    def match(self, commit: Commit) -> Optional[int]:
        """匹配 Commit 作者到用户 ID。"""
        # 1. Email 完全匹配
        if commit.author_email:
            email_lower = commit.author_email.lower()
            if email_lower in self.email_map:
                return self.email_map[email_lower].id
        
        # 2. 姓名匹配
        if commit.author_name and commit.author_name.lower() in self.name_map:
            return self.name_map[commit.author_name.lower()].id
        
        # 3. Email 前缀匹配用户名
        if commit.author_email:
            prefix = commit.author_email.split('@')[0].lower()
            if prefix in self.username_map:
                return self.username_map[prefix].id
        
        return None


class UserResolver:
    """用户解析器，将 gitlab_id 映射到内部用户 ID。"""
    
    def __init__(self, session: Session, client: GitLabClient):
        self.session = session
        self.client = client
        self.cache: Dict[int, int] = {}  # gitlab_id -> internal_id
        self._load_cache()
    
    def _load_cache(self):
        """加载现有用户到缓存。"""
        users = self.session.query(User).filter(User.gitlab_id.isnot(None)).all()
        for u in users:
            self.cache[u.gitlab_id] = u.id
    
    def resolve(self, gitlab_id: int) -> Optional[int]:
        """解析 GitLab 用户 ID 到内部 ID。"""
        if gitlab_id in self.cache:
            return self.cache[gitlab_id]
        
        # 从 API 获取并创建用户
        try:
            user_data = self.client.get_user(gitlab_id)
            user = User(
                gitlab_id=gitlab_id,
                username=user_data.get('username'),
                name=user_data.get('name'),
                email=user_data.get('email'),
                state=user_data.get('state'),
            )
            self.session.add(user)
            self.session.flush()
            self.cache[gitlab_id] = user.id
            return user.id
        except Exception as e:
            logger.warning(f"Failed to resolve user {gitlab_id}: {e}")
            return None


class GitLabWorker(BaseWorker):
    """GitLab 数据采集 Worker。
    
    支持全量同步和增量同步，包含断点续传功能。
    
    同步数据类型:
    - 项目元数据
    - Commits (提交)
    - Issues (议题)
    - Merge Requests (合并请求)
    - Pipelines (流水线)
    - Deployments (部署)
    - Notes (评论)
    - Tags (标签)
    - Branches (分支)
    """
    
    def __init__(self, session: Session, client: GitLabClient, enable_deep_analysis: bool = False):
        super().__init__(session, client)
        self.enable_deep_analysis = enable_deep_analysis
        self.identity_matcher = None  # Lazy init
        self.user_resolver = None     # Lazy init
    
    def process_task(self, task: dict) -> None:
        """处理 GitLab 同步任务。
        
        Args:
            task: {
                "source": "gitlab",
                "project_id": int,
                "job_type": "full" | "incremental"
            }
        """
        project_id = task.get('project_id')
        job_type = task.get('job_type', 'full')
        
        logger.info(f"Processing GitLab task: project_id={project_id}, job_type={job_type}")
        
        try:
            # 1. 同步项目元数据
            project = self._sync_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            project.sync_status = 'SYNCING'
            project.last_synced_at = datetime.now(timezone.utc)
            self.session.commit()
            
            # 获取增量同步起始时间
            since = None
            if job_type == 'incremental' and project.last_synced_at:
                since = project.last_synced_at.isoformat()
            
            # 初始化解析器
            self.user_resolver = UserResolver(self.session, self.client)
            
            # 2. 同步各类数据
            commits_count = self._sync_commits(project, since)
            issues_count = self._sync_issues(project, since)
            mrs_count = self._sync_merge_requests(project, since)
            pipelines_count = self._sync_pipelines(project)
            deployments_count = self._sync_deployments(project)
            tags_count = self._sync_tags(project)
            branches_count = self._sync_branches(project)
            
            # 3. 身份匹配
            self._match_identities(project)
            
            # 4. 更新项目状态
            project.sync_status = 'COMPLETED'
            project.last_activity_at = datetime.now(timezone.utc)
            self.session.commit()
            
            # 记录日志
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
            
            # 更新项目状态为失败
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
        """同步项目元数据。"""
        try:
            p_data = self.client.get_project(project_id)
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None
        
        project = self.session.query(Project).filter_by(id=project_id).first()
        if not project:
            project = Project(id=project_id)
            self.session.add(project)
        
        project.name = p_data.get('name')
        project.path_with_namespace = p_data.get('path_with_namespace')
        project.description = p_data.get('description')
        project.star_count = p_data.get('star_count')
        project.forks_count = p_data.get('forks_count')
        project.open_issues_count = p_data.get('open_issues_count')
        project.storage_size = p_data.get('statistics', {}).get('storage_size')
        project.commit_count = p_data.get('statistics', {}).get('commit_count')
        project.raw_data = p_data
        
        return project
    
    def _sync_commits(self, project: Project, since: Optional[str] = None) -> int:
        """同步提交记录 (支持流式处理和分批提交)。"""
        return self._process_generator(
            self.client.get_project_commits(project.id, since=since),
            lambda batch: self._save_commits_batch(project, batch)
        )

    def _save_commits_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存 Commits。"""
        ids = [item['id'] for item in batch]
        existing = self.session.query(Commit).filter(
            Commit.project_id == project.id,
            Commit.id.in_(ids)
        ).all()
        existing_map = {c.id: c for c in existing}
        
        for data in batch:
            commit = existing_map.get(data['id'])
            if not commit:
                commit = Commit(
                    id=data['id'],
                    project_id=project.id,
                    short_id=data.get('short_id'),
                    title=data.get('title'),
                    author_name=data.get('author_name'),
                    author_email=data.get('author_email'),
                    message=data.get('message'),
                    raw_data=data
                )
                self.session.add(commit)
            
            # 解析时间
            if data.get('committed_date'):
                try:
                    commit.committed_date = datetime.fromisoformat(
                        data['committed_date'].replace('Z', '+00:00')
                    )
                except:
                    pass
            
            # 深度分析
            if self.enable_deep_analysis and not commit.additions:
                self._analyze_commit_diff(project.id, commit)
    
    def _sync_issues(self, project: Project, since: Optional[str] = None) -> int:
        """同步 Issues (支持流式处理)。"""
        return self._process_generator(
            self.client.get_project_issues(project.id, since=since),
            lambda batch: self._save_issues_batch(project, batch)
        )

    def _save_issues_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存 Issues。"""
        ids = [item['id'] for item in batch]
        existing = self.session.query(Issue).filter(
            Issue.project_id == project.id,
            Issue.id.in_(ids)
        ).all()
        existing_map = {i.id: i for i in existing}
        
        for data in batch:
            issue = existing_map.get(data['id'])
            if not issue:
                issue = Issue(id=data['id'], project_id=project.id)
                self.session.add(issue)
            
            issue.iid = data.get('iid')
            issue.title = data.get('title')
            issue.description = data.get('description')
            issue.state = data.get('state')
            issue.labels = data.get('labels')
            issue.time_estimate = data.get('time_stats', {}).get('time_estimate')
            issue.total_time_spent = data.get('time_stats', {}).get('total_time_spent')
            issue.raw_data = data
            
            # 解析作者
            if data.get('author', {}).get('id'):
                issue.author_id = self.user_resolver.resolve(data['author']['id'])
    
    def _sync_merge_requests(self, project: Project, since: Optional[str] = None) -> int:
        """同步 Merge Requests (支持流式处理)。"""
        return self._process_generator(
            self.client.get_project_merge_requests(project.id, since=since),
            lambda batch: self._save_mrs_batch(project, batch)
        )

    def _save_mrs_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存 MRs。"""
        ids = [item['id'] for item in batch]
        existing = self.session.query(MergeRequest).filter(
            MergeRequest.project_id == project.id,
            MergeRequest.id.in_(ids)
        ).all()
        existing_map = {m.id: m for m in existing}
        
        for data in batch:
            mr = existing_map.get(data['id'])
            if not mr:
                mr = MergeRequest(id=data['id'], project_id=project.id)
                self.session.add(mr)
            
            mr.iid = data.get('iid')
            mr.title = data.get('title')
            mr.description = data.get('description')
            mr.state = data.get('state')
            mr.author_username = data.get('author', {}).get('username')
            mr.reviewers = data.get('reviewers')
            mr.raw_data = data
            
            # 解析时间
            for field in ['created_at', 'updated_at', 'merged_at', 'closed_at']:
                if data.get(field):
                    try:
                        setattr(mr, field, datetime.fromisoformat(
                            data[field].replace('Z', '+00:00')
                        ))
                    except:
                        pass
            
            # 解析作者
            if data.get('author', {}).get('id'):
                mr.author_id = self.user_resolver.resolve(data['author']['id'])
    
    def _sync_pipelines(self, project: Project) -> int:
        """同步流水线 (支持流式处理)。"""
        return self._process_generator(
            self.client.get_project_pipelines(project.id),
            lambda batch: self._save_pipelines_batch(project, batch)
        )

    def _save_pipelines_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存流水线。"""
        ids = [item['id'] for item in batch]
        existing = self.session.query(Pipeline).filter(
            Pipeline.project_id == project.id,
            Pipeline.id.in_(ids)
        ).all()
        existing_map = {p.id: p for p in existing}
        
        for data in batch:
            pipeline = existing_map.get(data['id'])
            if not pipeline:
                pipeline = Pipeline(id=data['id'], project_id=project.id)
                self.session.add(pipeline)
            
            pipeline.status = data.get('status')
            pipeline.ref = data.get('ref')
            pipeline.sha = data.get('sha')
            pipeline.source = data.get('source')
            pipeline.raw_data = data
    
    def _sync_deployments(self, project: Project) -> int:
        """同步部署记录 (支持流式处理)。"""
        return self._process_generator(
            self.client.get_project_deployments(project.id),
            lambda batch: self._save_deployments_batch(project, batch)
        )

    def _save_deployments_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存部署记录。"""
        ids = [item['id'] for item in batch]
        existing = self.session.query(Deployment).filter(
            Deployment.project_id == project.id,
            Deployment.id.in_(ids)
        ).all()
        existing_map = {d.id: d for d in existing}
        
        for data in batch:
            deploy = existing_map.get(data['id'])
            if not deploy:
                deploy = Deployment(id=data['id'], project_id=project.id)
                self.session.add(deploy)
            
            deploy.iid = data.get('iid')
            deploy.status = data.get('status')
            deploy.ref = data.get('ref')
            deploy.sha = data.get('sha')
            deploy.environment = data.get('environment', {}).get('name')
            deploy.raw_data = data
    
    def _sync_tags(self, project: Project) -> int:
        """同步标签 (支持流式处理)。"""
        count = self._process_generator(
            self.client.get_project_tags(project.id),
            lambda batch: self._save_tags_batch(project, batch)
        )
        project.tags_count = count
        return count

    def _save_tags_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存标签。"""
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
        """同步分支 (支持流式处理)。"""
        return self._process_generator(
            self.client.get_project_branches(project.id),
            lambda batch: self._save_branches_batch(project, batch)
        )

    def _save_branches_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存分支。"""
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
    
    def _match_identities(self, project: Project) -> None:
        """匹配未关联用户的 Commits。"""
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
    
    def _analyze_commit_diff(self, project_id: int, commit: Commit) -> None:
        """分析提交的 Diff (深度分析模式)。"""
        try:
            diffs = self.client.get_commit_diff(project_id, commit.id)
            
            total_additions = 0
            total_deletions = 0
            
            for diff in diffs:
                file_path = diff.get('new_path', diff.get('old_path', ''))
                
                if DiffAnalyzer.is_ignored(file_path):
                    continue
                
                diff_text = diff.get('diff', '')
                stats = DiffAnalyzer.analyze_diff(diff_text, file_path)
                
                total_additions += stats['code_added']
                total_deletions += stats['code_deleted']
                
                # 保存文件级统计
                file_stats = CommitFileStats(
                    commit_id=commit.id,
                    file_path=file_path,
                    language=file_path.split('.')[-1] if '.' in file_path else None,
                    code_added=stats['code_added'],
                    code_deleted=stats['code_deleted'],
                    comment_added=stats['comment_added'],
                    comment_deleted=stats['comment_deleted'],
                    blank_added=stats['blank_added'],
                    blank_deleted=stats['blank_deleted']
                )
                self.session.add(file_stats)
            
            commit.additions = total_additions
            commit.deletions = total_deletions
            commit.total = total_additions + total_deletions
            
        except Exception as e:
            logger.warning(f"Failed to analyze diff for commit {commit.id}: {e}")

    def _process_generator(self, generator, processor_func, batch_size: int = 500) -> int:
        """通用生成器处理逻辑 (流式 buffer + 批量回调)。
        
        Args:
            generator: 数据生成器
            processor_func: 批处理回调函数 func(batch_list)
            batch_size: 批次大小
            
        Returns:
            int: 处理的总条数
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


# 注册插件
PluginRegistry.register_worker('gitlab', GitLabWorker)

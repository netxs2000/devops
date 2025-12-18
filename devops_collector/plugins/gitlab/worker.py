"""GitLab 数据采集 Worker"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from .client import GitLabClient

from devops_collector.models import (
    Project, Commit, Issue, MergeRequest, Pipeline, 
    Deployment, Note, Tag, Branch, User, Organization,
    CommitFileStats, SyncLog, GitLabGroup, GitLabGroupMember, Milestone,
    IdentityMapping
)
from devops_collector.core.identity_manager import IdentityManager

logger = logging.getLogger(__name__)


class DiffAnalyzer:
    """代码差异分析器，将 Git diff 拆分为代码/注释/空行三类。"""
    
    COMMENT_SYMBOLS = {
        'py': '#', 'rb': '#', 'sh': '#', 'yaml': '#', 'yml': '#', 
        'dockerfile': '#', 'pl': '#', 'r': '#',
        'java': '//', 'js': '//', 'ts': '//', 'c': '//', 'cpp': '//', 
        'cs': '//', 'go': '//', 'rs': '//', 'swift': '//', 'kt': '//', 
        'scala': '//', 'php': '//',
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
        """构建 GitLab 用户身份索引以进行规则匹配。"""
        # 只索引来源为 gitlab 的身份映射
        mappings = self.session.query(IdentityMapping).filter_by(source='gitlab').all()
        
        self.email_map = {}    # {email.lower: user_id}
        self.username_map = {} # {external_id.lower: user_id}
        self.name_map = {}     # {external_name.lower: user_id}
        
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
        
        # 1. 首先按 author 的 email 和 gitlab 的 email 匹配
        if email in self.email_map:
            return self.email_map[email]
            
        # 2. author_name 和 gitlab 的 username 匹配
        if name in self.username_map:
            return self.username_map[name]
            
        # 3. author_name 和 gitlab 的 name 匹配
        if name in self.name_map:
            return self.name_map[name]
            
        # 4. 截取 author 的 email 前缀和 gitlab 的 username 匹配
        if email and '@' in email:
            prefix = email.split('@')[0]
            if prefix in self.username_map:
                return self.username_map[prefix]
        
        # 如果以上都没匹配到，利用 IdentityManager 创建/查找一个占位用户
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
            
            # GitLab 特色逻辑：从 skype 字段提取部门并映射到 Center 级组织
            dept_name = user_data.get('skype')
            if dept_name:
                user.department = dept_name
                # 寻找或创建 Center 级组织
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


class GitLabWorker(BaseWorker):
    """GitLab 数据采集 Worker。"""
    
    def __init__(self, session: Session, client: GitLabClient, enable_deep_analysis: bool = False):
        super().__init__(session, client)
        self.enable_deep_analysis = enable_deep_analysis
        self.identity_matcher = None 
        self.user_resolver = None 
    
    def process_task(self, task: dict) -> None:
        """处理 GitLab 同步任务。"""
        project_id = task.get('project_id')
        job_type = task.get('job_type', 'full')
        
        logger.info(f"Processing GitLab task: project_id={project_id}, job_type={job_type}")
        
        try:
            project = self._sync_project(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            project.sync_status = 'SYNCING'
            project.last_synced_at = datetime.now(timezone.utc)
            self.session.commit()
            
            since = None
            if job_type == 'incremental' and project.last_synced_at:
                since = project.last_synced_at.isoformat()
            
            self.user_resolver = UserResolver(self.session, self.client)
            
            commits_count = self._sync_commits(project, since)
            issues_count = self._sync_issues(project, since)
            mrs_count = self._sync_merge_requests(project, since)
            pipelines_count = self._sync_pipelines(project)
            deployments_count = self._sync_deployments(project)
            tags_count = self._sync_tags(project)
            branches_count = self._sync_branches(project)
            milestones_count = self._sync_milestones(project)
            
            self._match_identities(project)
            
            project.sync_status = 'COMPLETED'
            project.last_activity_at = datetime.now(timezone.utc)
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
        """同步项目元数据。"""
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
            
        return project

    def _sync_commits(self, project: Project, since: Optional[str]) -> int:
        count = self._process_generator(
            self.client.get_project_commits(project.id, since=since),
            lambda batch: self._save_commits_batch(project, batch)
        )
        return count

    def _save_commits_batch(self, project: Project, batch: List[dict]) -> None:
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
        
        if self.enable_deep_analysis and new_commits:
            pass

    def _sync_issues(self, project: Project, since: Optional[str]) -> int:
        count = self._process_generator(
            self.client.get_project_issues(project.id, since=since),
            lambda batch: self._save_issues_batch(project, batch)
        )
        return count

    def _save_issues_batch(self, project: Project, batch: List[dict]) -> None:
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

    def _sync_merge_requests(self, project: Project, since: Optional[str]) -> int:
        return self._process_generator(
            self.client.get_project_merge_requests(project.id, since=since),
            lambda batch: self._save_mrs_batch(project, batch)
        )

    def _save_mrs_batch(self, project: Project, batch: List[dict]) -> None:
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
            
            if data.get('merged_at'):
                mr.merged_at = datetime.fromisoformat(data['merged_at'].replace('Z', '+00:00'))
            if data.get('closed_at'):
                mr.closed_at = datetime.fromisoformat(data['closed_at'].replace('Z', '+00:00'))
                
            if data.get('author'):
                if self.user_resolver:
                    uid = self.user_resolver.resolve(data['author']['id'])
                    mr.author_id = uid

    def _sync_pipelines(self, project: Project) -> int:
        return self._process_generator(
            self.client.get_project_pipelines(project.id),
            lambda batch: self._save_pipelines_batch(project, batch)
        )

    def _save_pipelines_batch(self, project: Project, batch: List[dict]) -> None:
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
        return self._process_generator(
            self.client.get_project_deployments(project.id),
            lambda batch: self._save_deployments_batch(project, batch)
        )
    
    def _save_deployments_batch(self, project: Project, batch: List[dict]) -> None:
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
        count = self._process_generator(
            self.client.get_project_tags(project.id),
            lambda batch: self._save_tags_batch(project, batch)
        )
        project.tags_count = count
        return count

    def _save_tags_batch(self, project: Project, batch: List[dict]) -> None:
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
        return self._process_generator(
            self.client.get_project_branches(project.id),
            lambda batch: self._save_branches_batch(project, batch)
        )

    def _save_branches_batch(self, project: Project, batch: List[dict]) -> None:
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
        """同步里程碑 (支持流式处理)。"""
        return self._process_generator(
            self.client.get_project_milestones(project.id),
            lambda batch: self._save_milestones_batch(project, batch)
        )

    def _save_milestones_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存里程碑。"""
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

    def _match_identities(self, project: Project) -> None:
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
    
    def _process_generator(self, generator, processor_func, batch_size: int = 500) -> int:
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

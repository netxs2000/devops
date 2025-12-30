import gitlab
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from devops_collector.config import Config
from devops_collector.gitlab_sync.models.issue_metadata import IssueMetadata
from devops_collector.core.schemas import GitLabUserSchema

class GitLabSyncService:
    """GitLab 数据同步服务 (实现部门隔离逻辑)
    
    1. 用户部门: 取自 GitLab User.skype
    2. 项目部门: 取自项目顶级群组的 Description
    """

    def __init__(self):
        """初始化 GitLab 客户端"""
        self.gl = gitlab.Gitlab(Config.GITLAB_URL, private_token=Config.GITLAB_PRIVATE_TOKEN)
        # 缓存群组部门信息，减少 API 调用
        self._group_dept_cache = {}

    def get_top_level_group_dept_name(self, project_id: int) -> str:
        """获取项目顶级群组的描述作为部门中文名
        
        Args:
            project_id: GitLab 项目 ID
            
        Returns:
            str: 部门中文名 (顶级群组描述)
        """
        try:
            project = self.gl.projects.get(project_id)
            # 获取全路径并提取顶级群组名
            full_path = project.attributes['namespace']['full_path']
            top_group_path = full_path.split('/')[0]

            if top_group_path in self._group_dept_cache:
                return self._group_dept_cache[top_group_path]

            top_group = self.gl.groups.get(top_group_path)
            dept_name = top_group.description.strip() if top_group.description else "UNKNOWN_DEPT"
            
            self._group_dept_cache[top_group_path] = dept_name
            return dept_name
        except Exception as e:
            print(f"Error fetching top group dept for project {project_id}: {e}")
            return "UNKNOWN_DEPT"

    def sync_issue(self, db: Session, gitlab_issue_data: dict, project_id: int):
        """同步单个 Issue 并应用部门隔离逻辑
        
        Args:
            db: 数据库会话
            gitlab_issue_data: GitLab API 返回的 Issue 数据 (dict)
            project_id: 项目 ID
        """
        issue_iid = gitlab_issue_data['iid']
        
        # 1. 获取项目所属部门中文名
        dept_name = self.get_top_level_group_dept_name(project_id)
        
        # 2. 获取提报人部门中文名 (从 Skype 字段)
        author_data = gitlab_issue_data.get('author', {})
        author_username = author_data.get('username')
        author_dept_name = "UNKNOWN"
        
        if author_username:
            try:
                # 实时从 GitLab 获取用户 Profile 里的 Skype
                author_user_raw = self.gl.users.get(author_data['id'])
                # 使用 Pydantic 自动处理别名 (skypeid -> skype)
                author_schema = GitLabUserSchema.model_validate(author_user_raw.attributes)
                author_dept_name = author_schema.skype or "UNKNOWN"
            except Exception:
                pass

        # 3. 解析标签获取优先级和类型 (示例逻辑)
        labels = gitlab_issue_data.get('labels', [])
        priority = "P2"
        issue_type = "bug"
        for label in labels:
            if label.startswith('P'):
                priority = label
            if label in ['requirement', 'task', 'bug']:
                issue_type = label

        # 4. Upsert 到本地镜像表
        db_issue = db.query(IssueMetadata).filter_by(
            gitlab_project_id=project_id, 
            gitlab_issue_iid=issue_iid
        ).first()

        if not db_issue:
            db_issue = IssueMetadata(
                gitlab_project_id=project_id,
                gitlab_issue_iid=issue_iid,
                global_issue_id=gitlab_issue_data['id']
            )

        db_issue.dept_name = dept_name
        db_issue.title = gitlab_issue_data['title']
        db_issue.state = gitlab_issue_data['state']
        db_issue.author_username = author_username
        db_issue.author_dept_name = author_dept_name
        db_issue.assignee_username = gitlab_issue_data.get('assignee', {}).get('username')
        db_issue.issue_type = issue_type
        db_issue.priority = priority
        db_issue.gitlab_created_at = gitlab_issue_data['created_at']
        db_issue.gitlab_updated_at = gitlab_issue_data['updated_at']
        db_issue.sync_status = 1

        db.add(db_issue)
        db.commit()

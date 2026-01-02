"""GitLab 基础客户端封装模块。

本模块提供统一的 GitLab API 交互入口，处理身份验证、异常重试以及通用的数据提取逻辑。

Typical Usage:
    client = GitLabClient()
    project = client.get_project(123)
"""
import logging
import gitlab
from typing import Any, Optional, List
from devops_collector.config import Config
logger = logging.getLogger(__name__)

class GitLabClient:
    """GitLab API 封装基类。

    提供对 python-gitlab 客户端的基础封装，管理身份验证与核心资源获取。

    Attributes:
        gl: python-gitlab.Gitlab 认证后的客户端实例。
    """

    def __init__(self):
        """初始化 GitLab 客户端并执行身份验证。

        Raises:
            Exception: 当 GitLab API 认证失败或网络连接超时。
        """
        try:
            self.gl = gitlab.Gitlab(Config.GITLAB_URL, private_token=Config.GITLAB_PRIVATE_TOKEN, timeout=30)
            self.gl.auth()
            logger.info('Successfully authenticated with GitLab API.')
        except Exception as e:
            logger.error(f'Failed to initialize GitLab client: {e}')
            raise

    def get_project(self, project_id: int) -> Optional[Any]:
        """获取项目实例。

        Args:
            project_id: GitLab 项目 ID。

        Returns:
            Project 实例或 None。
        """
        try:
            return self.gl.projects.get(project_id)
        except gitlab.exceptions.GitlabGetError:
            logger.warning(f'Project {project_id} not found.')
            return None
        except Exception as e:
            logger.error(f'Error fetching project {project_id}: {e}')
            return None

    def get_issue(self, project_id: int, issue_iid: int) -> Optional[Any]:
        """获取特定项目的 Issue。

        Args:
            project_id: 项目 ID。
            issue_iid: Issue 的 IID。

        Returns:
            Issue 实例或 None。
        """
        project = self.get_project(project_id)
        if not project:
            return None
        try:
            return project.issues.get(issue_iid)
        except Exception as e:
            logger.error(f'Error fetching issue {issue_iid} in project {project_id}: {e}')
            return None

    def get_issue_author_id(self, db: Session, project_id: int, issue_iid: int) -> Optional[str]:
        """获取 Issue 创建者的 MDM 全局用户 ID。

        Args:
            db (Session): 数据库会话。
            project_id (int): 项目 ID。
            issue_iid (int): Issue IID。

        Returns:
            Optional[str]: global_user_id 或 None。
        """
        from devops_collector.auth import services as auth_services
        issue = self.get_issue(project_id, issue_iid)
        if not issue:
            return None
        email = issue.attributes.get('author', {}).get('email')
        if not email:
            return None
        user = auth_services.get_user_by_email(db, email=email)
        return str(user.global_user_id) if user else None

    def get_project_stakeholders(self, db: Session, project_id: int) -> List[str]:
        """获取项目干系人的 MDM 用户 ID 列表。

        Args:
            db (Session): 数据库会话。
            project_id (int): 项目 ID。

        Returns:
            List[str]: 干系人 ID 列表。
        """
        from devops_collector.models import Project, Product, Location
        stakeholders = []
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.location_id:
            loc = db.query(Location).filter(Location.location_id == project.location_id).first()
            if loc and loc.manager_user_id:
                stakeholders.append(str(loc.manager_user_id))
        product = db.query(Product).filter(Product.project_id == project_id).first()
        if product:
            uids = [product.product_manager_id, product.dev_manager_id, product.test_manager_id]
            stakeholders.extend([str(uid) for uid in uids if uid])
        return list(set(stakeholders))
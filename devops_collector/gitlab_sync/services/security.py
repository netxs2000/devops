from sqlalchemy.orm import Query, Session
from sqlalchemy import or_
from typing import Any

from devops_collector.models.base_models import User
from devops_collector.gitlab_sync.models.issue_metadata import IssueMetadata

class IssueSecurityProvider:
    """工单安全隐私过滤提供者
    
    实现“所属权 OR 提报权”的并集可见性逻辑：
    1. 部门可见性：用户可以看到所属部门(Top-level Group)的所有工单。
    2. 个人可见性：用户可以看到自己作为提报人(Author)的所有工单，无论提给哪个部门。
    """

    @staticmethod
    def apply_issue_privacy_filter(db: Session, query: Query, current_user: User) -> Query:
        """应用工单隐私过滤逻辑
        
        Args:
            db: 数据库会话
            query: 初始查询对象 (IssueMetadata)
            current_user: 当前登录用户
            
        Returns:
            Query: 过滤后的查询对象
        """
        # 1. 获取用户部门中文名 (来自 mdm_organizations)
        user_dept_name = "UNKNOWN"
        if current_user.department:
            user_dept_name = current_user.department.org_name
            
        # 2. 获取用户 GitLab 账号名 (来自 identity_map)
        # 假设存储格式为 {"gitlab": {"username": "zhangsan"}}
        gitlab_username = None
        if current_user.identity_map and 'gitlab' in current_user.identity_map:
            gitlab_info = current_user.identity_map['gitlab']
            if isinstance(gitlab_info, dict):
                gitlab_username = gitlab_info.get('username')
            else:
                # 兼容旧格式或是直接存储的数字 ID，这里尝试匹配 username
                pass 

        # 3. 构造并集过滤条件
        conditions = [IssueMetadata.dept_name == user_dept_name]
        
        if gitlab_username:
            conditions.append(IssueMetadata.author_username == gitlab_username)
            
        # 4. 应用 OR 逻辑
        return query.filter(or_(*conditions)).filter(IssueMetadata.sync_status == 1)

    @staticmethod
    def get_visible_issues(db: Session, current_user: User) -> list:
        """直接获取当前用户可见的所有工单
        
        Args:
            db: 数据库会话
            current_user: 当前登录用户
            
        Returns:
            list: 可见工单列表
        """
        base_query = db.query(IssueMetadata)
        filtered_query = IssueSecurityProvider.apply_issue_privacy_filter(db, base_query, current_user)
        return filtered_query.all()

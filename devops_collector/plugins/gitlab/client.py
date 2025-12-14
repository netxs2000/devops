"""GitLab API 客户端

基于 BaseClient 实现的 GitLab REST API 封装。
复用原有 gitlab_client.py 的核心逻辑。
"""
from typing import List, Dict, Optional, Any
from devops_collector.core.base_client import BaseClient


class GitLabClient(BaseClient):
    """GitLab REST API 客户端。
    
    封装所有 GitLab 数据采集所需的 API 方法，包含：
    - 项目信息获取
    - 提交/分支/标签列表
    - 流水线/部署记录
    - Issue/MR/Note 数据
    
    Attributes:
        base_url: GitLab API 地址 (如 https://gitlab.com/api/v4)
    
    Example:
        client = GitLabClient(url="https://gitlab.com", token="xxx")
        project = client.get_project(123)
    """
    
    def __init__(self, url: str, token: str, rate_limit: int = 10):
        """初始化 GitLab 客户端。
        
        Args:
            url: GitLab 实例地址 (不含 /api/v4)
            token: GitLab Private Token
            rate_limit: 每秒请求限制
        """
        super().__init__(
            base_url=f"{url.rstrip('/')}/api/v4",
            auth_headers={'PRIVATE-TOKEN': token},
            rate_limit=rate_limit
        )
    
    def test_connection(self) -> bool:
        """测试 GitLab 连接。"""
        try:
            self._get("version")
            return True
        except Exception:
            return False
    
    def get_project(self, project_id: int) -> dict:
        """获取项目详情，包含统计信息。"""
        return self._get(f"projects/{project_id}", params={'statistics': True}).json()
    
    def get_group(self, group_id_or_path: str) -> dict:
        """获取群组详情。"""
        return self._get(f"groups/{group_id_or_path}").json()
    
    def get_project_commits(
        self, 
        project_id: int, 
        since: Optional[str] = None, 
        start_page: int = 1,
        per_page: int = 100
    ):
        """获取项目所有提交记录，自动处理分页 (Generator 模式)。"""
        page = start_page
        
        while True:
            params = {'per_page': per_page, 'page': page}
            if since:
                params['since'] = since
            
            response = self._get(f"projects/{project_id}/repository/commits", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_commit_diff(self, project_id: int, commit_sha: str) -> List[dict]:
        """获取提交的 Diff 详情。"""
        return self._get(f"projects/{project_id}/repository/commits/{commit_sha}/diff").json()
    
    def get_project_issues(
        self, 
        project_id: int, 
        since: Optional[str] = None,
        start_page: int = 1,
        per_page: int = 100
    ):
        """获取项目所有 Issues (Generator 模式)。"""
        page = start_page
        
        while True:
            params = {'per_page': per_page, 'page': page}
            if since:
                params['updated_after'] = since
            
            response = self._get(f"projects/{project_id}/issues", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_project_merge_requests(
        self, 
        project_id: int,
        since: Optional[str] = None,
        start_page: int = 1,
        per_page: int = 100
    ):
        """获取项目所有 MRs (Generator 模式)。"""
        page = start_page
        
        while True:
            params = {'per_page': per_page, 'page': page}
            if since:
                params['updated_after'] = since
            
            response = self._get(f"projects/{project_id}/merge_requests", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_project_pipelines(
        self, 
        project_id: int,
        start_page: int = 1,
        per_page: int = 100
    ):
        """获取项目所有流水线 (Generator 模式)。"""
        page = start_page
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"projects/{project_id}/pipelines", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_project_deployments(
        self, 
        project_id: int,
        start_page: int = 1,
        per_page: int = 100
    ):
        """获取项目所有部署记录 (Generator 模式)。"""
        page = start_page
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"projects/{project_id}/deployments", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_issue_notes(
        self, 
        project_id: int, 
        issue_iid: int,
        per_page: int = 100
    ):
        """获取 Issue 的所有评论 (Generator 模式)。"""
        page = 1
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"projects/{project_id}/issues/{issue_iid}/notes", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_mr_notes(
        self, 
        project_id: int, 
        mr_iid: int,
        per_page: int = 100
    ):
        """获取 MR 的所有评论 (Generator 模式)。"""
        page = 1
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"projects/{project_id}/merge_requests/{mr_iid}/notes", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_project_tags(
        self, 
        project_id: int,
        per_page: int = 100
    ):
        """获取项目所有标签 (Generator 模式)。"""
        page = 1
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"projects/{project_id}/repository/tags", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_project_branches(
        self, 
        project_id: int,
        per_page: int = 100
    ):
        """获取项目所有分支 (Generator 模式)。"""
        page = 1
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"projects/{project_id}/repository/branches", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_project_members(
        self, 
        project_id: int,
        per_page: int = 100
    ):
        """获取项目成员 (Generator 模式)。"""
        page = 1
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"projects/{project_id}/members/all", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1
    
    def get_user(self, user_id: int) -> dict:
        """获取用户详情。"""
        return self._get(f"users/{user_id}").json()
    
    def get_count(self, endpoint: str, params: Optional[Dict] = None) -> int:
        """获取资源总数 (从响应头提取)。"""
        response = self._get(endpoint, params={**(params or {}), 'per_page': 1})
        return int(response.headers.get('x-total', 0))

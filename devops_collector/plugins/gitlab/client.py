"""GitLab API 客户端"""
from typing import List, Dict, Optional, Any, Generator
from devops_collector.core.base_client import BaseClient


class GitLabClient(BaseClient):
    """GitLab REST API 客户端。"""
    
    def __init__(self, url: str, token: str, rate_limit: int = 10):
        super().__init__(
            base_url=f"{url.rstrip('/')}/api/v4",
            auth_headers={'PRIVATE-TOKEN': token},
            rate_limit=rate_limit
        )
    
    def test_connection(self) -> bool:
        try:
            self._get("version")
            return True
        except Exception:
            return False
    
    def get_project(self, project_id: int) -> dict:
        return self._get(f"projects/{project_id}", params={'statistics': True}).json()
    
    def get_group(self, group_id_or_path: str) -> dict:
        return self._get(f"groups/{group_id_or_path}").json()
    
    def get_project_commits(
        self, 
        project_id: int, 
        since: Optional[str] = None, 
        start_page: int = 1,
        per_page: int = 100
    ):
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
        return self._get(f"projects/{project_id}/repository/commits/{commit_sha}/diff").json()
    
    def get_project_issues(
        self, 
        project_id: int, 
        since: Optional[str] = None,
        start_page: int = 1,
        per_page: int = 100
    ):
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

    def get_mr_approvals(self, project_id: int, mr_iid: int) -> dict:
        """获取合并请求的审批详情。"""
        return self._get(f"projects/{project_id}/merge_requests/{mr_iid}/approvals").json()

    def get_mr_pipelines(self, project_id: int, mr_iid: int) -> List[dict]:
        """获取合并请求关联的流水线。"""
        return self._get(f"projects/{project_id}/merge_requests/{mr_iid}/pipelines").json()
    
    def get_project_tags(
        self, 
        project_id: int,
        per_page: int = 100
    ):
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
            
    def get_project_milestones(
        self, 
        project_id: int,
        per_page: int = 100
    ):
        """获取项目里程碑 (Generator 模式)。"""
        page = 1
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"projects/{project_id}/milestones", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1

    def get_user(self, user_id: int) -> dict:
        return self._get(f"users/{user_id}").json()
    
    def get_count(self, endpoint: str, params: Optional[Dict] = None) -> int:
        response = self._get(endpoint, params={**(params or {}), 'per_page': 1})
        return int(response.headers.get('x-total', 0))

    def get_group_members(
        self, 
        group_id: int,
        per_page: int = 100
    ):
        page = 1
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"groups/{group_id}/members", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1

    def get_packages(
        self, 
        project_id: int,
        per_page: int = 100
    ):
        """获取项目制品库下的包列表。"""
        page = 1
        
        while True:
            params = {'per_page': per_page, 'page': page}
            response = self._get(f"projects/{project_id}/packages", params=params)
            data = response.json()
            if not data:
                break
            
            for item in data:
                yield item
                
            page += 1

    def get_package_files(
        self, 
        project_id: int,
        package_id: int
    ) -> List[dict]:
        """获取包关联的文件列表。"""
        return self._get(f"projects/{project_id}/packages/{package_id}/package_files").json()

    def create_group_label(self, group_id: int, label_data: Dict) -> dict:
        """创建群组标签。"""
        return self._post(f"groups/{group_id}/labels", data=label_data).json()

    def create_project_label(self, project_id: int, label_data: Dict) -> dict:
        """创建项目标签。"""
        return self._post(f"projects/{project_id}/labels", data=label_data).json()

    def add_issue_label(self, project_id: int, issue_iid: int, labels: List[str]) -> dict:
        """为 Issue 添加标签。"""
        # GitLab API 支持使用 add_labels 参数
        return self._put(f"projects/{project_id}/issues/{issue_iid}", data={'add_labels': ','.join(labels)}).json()

    def add_issue_note(self, project_id: int, issue_iid: int, body: str) -> dict:
        """为 Issue 添加评论。"""
        return self._post(f"projects/{project_id}/issues/{issue_iid}/notes", data={'body': body}).json()

    def get_issue_state_events(self, project_id: int, issue_iid: int) -> Generator[Dict, None, None]:
        """获取 Issue 的状态变更事件。"""
        return self._get_paged_data(f"projects/{project_id}/issues/{issue_iid}/resource_state_events")

    def get_issue_label_events(self, project_id: int, issue_iid: int) -> Generator[Dict, None, None]:
        """获取 Issue 的标签变更事件。"""
        return self._get_paged_data(f"projects/{project_id}/issues/{issue_iid}/resource_label_events")

    def get_issue_milestone_events(self, project_id: int, issue_iid: int) -> Generator[Dict, None, None]:
        """获取 Issue 的里程碑变更事件。"""
        return self._get_paged_data(f"projects/{project_id}/issues/{issue_iid}/resource_milestone_events")

    def get_project_wiki_events(self, project_id: int) -> Generator[Dict, None, None]:
        """获取项目的 Wiki 事件。"""
        # 利用 events 接口过滤 wiki_page
        return self._get_paged_data(f"projects/{project_id}/events", params={'target_type': 'wiki_page'})

    def get_project_dependencies(self, project_id: int) -> Generator[Dict, None, None]:
        """获取项目依赖列表 (需开启 Dependency Scanning)。"""
        return self._get_paged_data(f"projects/{project_id}/dependencies")

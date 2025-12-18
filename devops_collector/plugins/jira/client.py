"""Jira REST API 客户端

支持 Jira 的基础认证、分页获取项目、看板、Sprint 和 Issue。
"""
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class JiraClient:
    """Jira API 客户端。"""
    
    def __init__(self, base_url: str, email: str, api_token: str):
        """初始化 Jira 客户端。
        
        Args:
            base_url: Jira 实例地址 (如 https://your-domain.atlassian.net)
            email: 用户邮箱
            api_token: API 令牌 (Token)
        """
        self.base_url = base_url.rstrip('/')
        self.auth = (email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """通用的 GET 请求方法。"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, auth=self.auth, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Jira API 请求失败: {url}, 错误: {e}")
            raise

    def get_projects(self) -> List[Dict[str, Any]]:
        """获取所有项目。"""
        return self._get("/rest/api/3/project")

    def get_boards(self, project_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取敏捷看板。"""
        params = {}
        if project_key:
            params["projectKeyOrId"] = project_key
        
        boards = []
        start_at = 0
        max_results = 50
        
        while True:
            params["startAt"] = start_at
            params["maxResults"] = max_results
            data = self._get("/rest/agile/1.0/board", params=params)
            boards.extend(data.get("values", []))
            
            if data.get("isLast", True):
                break
            start_at += max_results
            
        return boards

    def get_sprints(self, board_id: int) -> List[Dict[str, Any]]:
        """获取看板下的所有 Sprint。"""
        sprints = []
        start_at = 0
        max_results = 50
        
        while True:
            params = {"startAt": start_at, "maxResults": max_results}
            data = self._get(f"/rest/agile/1.0/board/{board_id}/sprint", params=params)
            sprints.extend(data.get("values", []))
            
            if data.get("isLast", True):
                break
            start_at += max_results
            
        return sprints

    def get_issues(self, jql: str) -> List[Dict[str, Any]]:
        """根据 JQL 查询获取 Issue。"""
        issues = []
        start_at = 0
        max_results = 100
        
        while True:
            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "expand": ["changelog"],
                "fields": ["summary", "description", "status", "priority", "issuetype", "assignee", "reporter", "creator", "created", "updated", "resolutiondate"]
            }
            data = self._get("/rest/api/3/search", params=params)
            issues.extend(data.get("issues", []))
            
            total = data.get("total", 0)
            start_at += len(data.get("issues", []))
            if start_at >= total or not data.get("issues"):
                break
                
        return issues

    def get_groups(self) -> List[Dict[str, Any]]:
        """获取全量用户组列表。"""
        data = self._get("/rest/api/3/groups/picker", params={"maxResults": 1000})
        return data.get("groups", [])

    def get_all_users(self) -> List[Dict[str, Any]]:
        """获取活跃用户列表。"""
        return self._get("/rest/api/3/users/search", params={"query": "", "maxResults": 1000})

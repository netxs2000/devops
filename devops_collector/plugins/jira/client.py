"""Jira REST API 客户端

支持 Jira 的基础认证、分页获取项目、看板、Sprint 和 Issue。
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)
import base64

from devops_collector.core.base_client import BaseClient


class JiraClient(BaseClient):
    """Jira API 客户端。"""

    def __init__(self, url: str, email: str, api_token: str, rate_limit: int = 5):
        """初始化 Jira 客户端。

        Args:
            url: Jira 实例地址 (如 https://your-domain.atlassian.net)
            email: 用户邮箱
            api_token: API 令牌 (Token)
            rate_limit: 每秒请求限制
        """
        auth_str = f"{email}:{api_token}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        super().__init__(
            base_url=url.rstrip("/"),
            auth_headers={
                "Authorization": f"Basic {encoded_auth}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            rate_limit=rate_limit,
        )

    def get_projects(self) -> list[dict[str, Any]]:
        """获取所有项目。"""
        response = self._get("/rest/api/3/project")
        return response.json()

    def test_connection(self) -> bool:
        """测试 Jira 连接。"""
        try:
            response = self._get("/rest/api/3/configuration")
            return response.status_code == 200
        except Exception:
            return False

    def get_boards(self, project_key: str | None = None) -> list[dict[str, Any]]:
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
            response = self._get("/rest/agile/1.0/board", params=params)
            data = response.json()
            boards.extend(data.get("values", []))
            if data.get("isLast", True):
                break
            start_at += max_results
        return boards

    def get_sprints(self, board_id: int) -> list[dict[str, Any]]:
        """获取看板下的所有 Sprint。"""
        sprints = []
        start_at = 0
        max_results = 50
        while True:
            params = {"startAt": start_at, "maxResults": max_results}
            response = self._get(f"/rest/agile/1.0/board/{board_id}/sprint", params=params)
            data = response.json()
            sprints.extend(data.get("values", []))
            if data.get("isLast", True):
                break
            start_at += max_results
        return sprints

    def get_issues(self, jql: str) -> list[dict[str, Any]]:
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
                "fields": [
                    "summary",
                    "description",
                    "status",
                    "priority",
                    "issuetype",
                    "assignee",
                    "reporter",
                    "creator",
                    "created",
                    "updated",
                    "resolutiondate",
                    "labels",
                    "fixVersions",
                    "timeoriginalestimate",
                    "timespent",
                    "timeestimate",
                    "issuelinks",
                ],
            }
            response = self._get("/rest/api/3/search", params=params)
            data = response.json()
            issues.extend(data.get("issues", []))
            total = data.get("total", 0)
            start_at += len(data.get("issues", []))
            if start_at >= total or not data.get("issues"):
                break
        return issues

    def get_groups(self) -> list[dict[str, Any]]:
        """获取全量用户组列表。"""
        response = self._get("/rest/api/3/groups/picker", params={"maxResults": 1000})
        return response.json().get("groups", [])

    def get_all_users(self) -> list[dict[str, Any]]:
        """获取活跃用户列表。"""
        response = self._get("/rest/api/3/users/search", params={"query": "", "maxResults": 1000})
        return response.json()

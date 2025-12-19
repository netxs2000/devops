"""禅道 (ZenTao) REST API 客户端 (全量版)

支持新版禅道 REST API，支持获取产品、执行 (迭代)、需求、缺陷、用例、结果、构建和发布。
"""
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

from devops_collector.core.base_client import BaseClient

class ZenTaoClient(BaseClient):
    """禅道 REST API 客户端 (支持 v1+ 接口)。"""
    
    def __init__(self, url: str, token: str, rate_limit: int = 5):
        """初始化禅道客户端。"""
        super().__init__(
            base_url=url.rstrip('/'),
            auth_headers={
                "Token": token,
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            rate_limit=rate_limit
        )

    def test_connection(self) -> bool:
        """测试禅道连接。"""
        try:
            response = self._get("/users")
            return response.status_code == 200
        except Exception:
            return False

    def get_products(self) -> List[Dict[Any, Any]]:
        """获取所有产品。"""
        response = self._get("/products")
        return response.json().get("products", [])

    def get_plans(self, product_id: int) -> List[Dict[Any, Any]]:
        """获取产品计划。"""
        response = self._get(f"/products/{product_id}/plans")
        return response.json().get("plans", [])

    def get_executions(self, project_id: Optional[int] = None) -> List[Dict[Any, Any]]:
        """获取执行 (迭代/Sprint)。"""
        # 禅道新版 REST API 中，Execution 可能归属于 Project
        endpoint = "/executions"
        if project_id:
            endpoint = f"/projects/{project_id}/executions"
        response = self._get(endpoint)
        return response.json().get("executions", [])

    def get_stories(self, product_id: int) -> List[Dict[str, Any]]:
        """获取需求。"""
        stories = []
        page = 1
        limit = 100
        while True:
            params = {"page": page, "limit": limit}
            response = self._get(f"/products/{product_id}/stories", params=params)
            data = response.json()
            current = data.get("stories", [])
            stories.extend(current)
            if len(stories) >= data.get("total", 0) or not current:
                break
            page += 1
        return stories

    def get_bugs(self, product_id: int) -> List[Dict[str, Any]]:
        """获取缺陷。"""
        bugs = []
        page = 1
        limit = 100
        while True:
            params = {"page": page, "limit": limit}
            response = self._get(f"/products/{product_id}/bugs", params=params)
            data = response.json()
            current = data.get("bugs", [])
            bugs.extend(current)
            if len(bugs) >= data.get("total", 0) or not current:
                break
            page += 1
        return bugs

    def get_test_cases(self, product_id: int) -> List[Dict[str, Any]]:
        """获取测试用例。"""
        response = self._get(f"/products/{product_id}/cases")
        return response.json().get("cases", [])

    def get_test_results(self, case_id: int) -> List[Dict[str, Any]]:
        """获取用例执行结果。"""
        response = self._get(f"/cases/{case_id}/results")
        return response.json().get("results", [])

    def get_builds(self, execution_id: int) -> List[Dict[str, Any]]:
        """获取执行下的构建 (Build)。"""
        response = self._get(f"/executions/{execution_id}/builds")
        return response.json().get("builds", [])

    def get_releases(self, product_id: int) -> List[Dict[str, Any]]:
        """获取发布 (Release)。"""
        response = self._get(f"/products/{product_id}/releases")
        return response.json().get("releases", [])

    def get_actions(self, product_id: int) -> List[Dict[str, Any]]:
        """获取产品的操作记录 (Action Logs)。"""
        response = self._get(f"/products/{product_id}/actions")
        return response.json().get("actions", [])

    def get_departments(self) -> List[Dict[str, Any]]:
        """获取组织架构部门列表。"""
        response = self._get("/departments")
        return response.json().get("departments", [])

    def get_users(self) -> List[Dict[str, Any]]:
        """获取用户列表。"""
        # 注意：禅道用户列表可能需要分页，此处先实现基础获取
        response = self._get("/users")
        return response.json().get("users", [])

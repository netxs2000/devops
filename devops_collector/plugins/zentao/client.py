"""禅道 (ZenTao) REST API 客户端 (全量版)

支持新版禅道 REST API，支持获取产品、执行 (迭代)、需求、缺陷、用例、结果、构建和发布。
"""
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ZenTaoClient:
    """禅道 REST API 客户端 (支持 v1+ 接口)。"""
    
    def __init__(self, base_url: str, token: str):
        """初始化禅道客户端。"""
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Token": token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """通用的 GET 请求方法。"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"ZenTao API 请求失败: {url}, 错误: {e}")
            raise

    def get_products(self) -> List[Dict[Any, Any]]:
        """获取所有产品。"""
        data = self._get("/products")
        return data.get("products", [])

    def get_plans(self, product_id: int) -> List[Dict[Any, Any]]:
        """获取产品计划。"""
        data = self._get(f"/products/{product_id}/plans")
        return data.get("plans", [])

    def get_executions(self, project_id: Optional[int] = None) -> List[Dict[Any, Any]]:
        """获取执行 (迭代/Sprint)。"""
        # 禅道新版 REST API 中，Execution 可能归属于 Project
        endpoint = "/executions"
        if project_id:
            endpoint = f"/projects/{project_id}/executions"
        data = self._get(endpoint)
        return data.get("executions", [])

    def get_stories(self, product_id: int) -> List[Dict[str, Any]]:
        """获取需求。"""
        stories = []
        page = 1
        limit = 100
        while True:
            params = {"page": page, "limit": limit}
            data = self._get(f"/products/{product_id}/stories", params=params)
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
            data = self._get(f"/products/{product_id}/bugs", params=params)
            current = data.get("bugs", [])
            bugs.extend(current)
            if len(bugs) >= data.get("total", 0) or not current:
                break
            page += 1
        return bugs

    def get_test_cases(self, product_id: int) -> List[Dict[str, Any]]:
        """获取测试用例。"""
        data = self._get(f"/products/{product_id}/cases")
        return data.get("cases", [])

    def get_test_results(self, case_id: int) -> List[Dict[str, Any]]:
        """获取用例执行结果。"""
        data = self._get(f"/cases/{case_id}/results")
        return data.get("results", [])

    def get_builds(self, execution_id: int) -> List[Dict[str, Any]]:
        """获取执行下的构建 (Build)。"""
        data = self._get(f"/executions/{execution_id}/builds")
        return data.get("builds", [])

    def get_releases(self, product_id: int) -> List[Dict[str, Any]]:
        """获取发布 (Release)。"""
        data = self._get(f"/products/{product_id}/releases")
        return data.get("releases", [])

    def get_actions(self, product_id: int) -> List[Dict[str, Any]]:
        """获取产品的操作记录 (Action Logs)。"""
        data = self._get(f"/products/{product_id}/actions")
        return data.get("actions", [])

    def get_departments(self) -> List[Dict[str, Any]]:
        """获取组织架构部门列表。"""
        data = self._get("/departments")
        return data.get("departments", [])

    def get_users(self) -> List[Dict[str, Any]]:
        """获取用户列表。"""
        # 注意：禅道用户列表可能需要分页，此处先实现基础获取
        data = self._get("/users")
        return data.get("users", [])

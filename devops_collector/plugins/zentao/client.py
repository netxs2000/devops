"""禅道 (ZenTao) REST API 客户端 (全量版)

支持新版禅道 REST API，支持获取产品、执行 (迭代)、需求、缺陷、用例、结果、构建和发布。
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)
from devops_collector.core.base_client import BaseClient


class ZenTaoClient(BaseClient):
    """禅道 REST API 客户端 (支持 v1+ 接口)。"""

    def __init__(
        self,
        url: str,
        token: str,
        account: str | None = None,
        password: str | None = None,
        rate_limit: int = 5,
    ):
        """初始化禅道客户端。"""
        super().__init__(
            base_url=url.rstrip("/"),
            auth_headers={"Token": token, "Accept": "application/json", "Content-Type": "application/json"},
            rate_limit=rate_limit,
            verify=False,
        )
        self.account = account
        self.password = password
        print("DEBUG: ZenTaoClient v2 initializing...")

    def _refresh_token(self) -> bool:
        """使用账号密码刷新 Token。"""
        print(f"DEBUG: _refresh_token called, account={getattr(self, 'account', None)}")
        if not self.account or not self.password:
            return False
        try:
            url = f"{self.base_url}/tokens"
            logger.info(f"Refreshing ZenTao token for {self.account}...")
            # 注意：使用 requests 直接调用以避免重入
            import requests

            resp = requests.post(url, json={"account": self.account, "password": self.password}, verify=False, timeout=10)
            if resp.status_code in [200, 201]:
                new_token = resp.json().get("token")
                if new_token:
                    self.headers["Token"] = new_token
                    logger.info("Successfully refreshed ZenTao token.")
                    return True
            logger.error(f"Failed to refresh ZenTao token: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Error refreshing ZenTao token: {e}")
        return False

    def _get(self, endpoint: str, params: dict[str, Any] | None = None, allow_404: bool = False, is_retry: bool = False) -> Any:
        """发送 GET 请求，支持 Token 自动过期重连及 404 容错。"""
        import requests
        try:
            return super()._get(endpoint, params)
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                # 处理 401 认证过期
                if e.response.status_code == 401 and not is_retry:
                    logger.info(f"Auth 401 detected for {endpoint}, attempting token refresh...")
                    if self._refresh_token():
                        # 重新请求一次，标记为 is_retry 以防死循环
                        return self._get(endpoint, params=params, allow_404=allow_404, is_retry=True)
                
                # 处理 404 容错
                if e.response.status_code == 404 and allow_404:
                    return e.response
            raise
        except Exception as e:
            raise

    def test_connection(self) -> bool:
        """测试禅道连接。"""
        try:
            response = self._get("users")
            return response.status_code == 200
        except Exception:
            return False

    def _handle_list_response(self, response: Any, key: str) -> list[dict[str, Any]]:
        """处理可能直接返回列表或包含在字典中的列表响应，支持 404。"""
        if response.status_code == 404:
            return []
        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get(key, [])
        return []

    def get_products(self) -> list[dict[Any, Any]]:
        """获取所有产品。"""
        response = self._get("products")
        return self._handle_list_response(response, "products")

    def get_plans(self, product_id: int) -> list[dict[Any, Any]]:
        """获取产品计划。"""
        response = self._get(f"products/{product_id}/plans", allow_404=True)
        return self._handle_list_response(response, "plans")

    def get_executions(self, project_id: int | None = None, product_id: int | None = None) -> list[dict[Any, Any]]:
        """获取执行 (迭代/Sprint/阶段)。"""
        endpoint = "executions"
        if project_id:
            endpoint = f"projects/{project_id}/executions"
        elif product_id:
            endpoint = f"products/{product_id}/executions"
            
        response = self._get(endpoint, allow_404=True)
        return self._handle_list_response(response, "executions")

    def get_projects(self) -> list[dict[Any, Any]]:
        """获取项目 (Project)。"""
        return self._get_paged_list("projects", "projects")

    def get_programs(self) -> list[dict[Any, Any]]:
        """获取项目集 (Program)。"""
        return self._get_paged_list("programs", "programs")

    def _get_paged_list(self, endpoint: str, key: str) -> list[dict[str, Any]]:
        """统一的分页列表获取逻辑。"""
        items = []
        page = 1
        limit = 100
        max_pages = 1000  # 安全保护
        while page <= max_pages:
            params = {"page": page, "limit": limit}
            try:
                response = self._get(endpoint, params=params, allow_404=True)
                if response.status_code == 404:
                    break
                data = response.json()
                current = data.get(key, []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                items.extend(current)
                if isinstance(data, dict):
                    total = data.get("total", 0)
                    if len(items) >= total or not current:
                        break
                else:
                    break
            except Exception as e:
                logger.error(f"Error fetching {endpoint} page {page}: {e}")
                break
            page += 1
        return items

    def get_stories(self, product_id: int) -> list[dict[str, Any]]:
        """获取需求。"""
        stories = []
        page = 1
        limit = 100
        max_pages = 1000  # 安全保护
        while page <= max_pages:
            params = {"page": page, "limit": limit}
            try:
                response = self._get(f"products/{product_id}/stories", params=params, allow_404=True)
                if response.status_code == 404:
                    break
                data = response.json()
                # 这里的分页结构通常是 {'stories': [...], 'total': ...}
                current = data.get("stories", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                stories.extend(current)
                if isinstance(data, dict):
                    total = data.get("total", 0)
                    if len(stories) >= total or not current:
                        break
                else:
                    break
                page += 1
            except Exception as e:
                logger.error(f"Error fetching stories for product {product_id} page {page}: {e}")
                break
        return stories

    def get_bugs(self, product_id: int) -> list[dict[str, Any]]:
        """获取缺陷。"""
        bugs = []
        page = 1
        limit = 100
        max_pages = 1000  # 安全保护
        while page <= max_pages:
            params = {"page": page, "limit": limit}
            try:
                response = self._get(f"products/{product_id}/bugs", params=params, allow_404=True)
                if response.status_code == 404:
                    break
                data = response.json()
                current = data.get("bugs", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                bugs.extend(current)
                if isinstance(data, dict):
                    total = data.get("total", 0)
                    if len(bugs) >= total or not current:
                        break
                else:
                    break
                page += 1
            except Exception as e:
                logger.error(f"Error fetching bugs for product {product_id} page {page}: {e}")
                break
        return bugs

    def get_test_cases(self, product_id: int) -> list[dict[str, Any]]:
        """获取测试用例。"""
        response = self._get(f"products/{product_id}/testcases", allow_404=True)
        return self._handle_list_response(response, "testcases")

    def get_test_results(self, case_id: int) -> list[dict[str, Any]]:
        """获取用例执行结果。"""
        response = self._get(f"testcases/{case_id}/results", allow_404=True)
        return self._handle_list_response(response, "results")

    def get_builds(self, execution_id: int) -> list[dict[str, Any]]:
        """获取执行下的构建 (Build)。"""
        response = self._get(f"executions/{execution_id}/builds", allow_404=True)
        return self._handle_list_response(response, "builds")

    def get_releases(self, product_id: int) -> list[dict[str, Any]]:
        """获取发布 (Release)。"""
        response = self._get(f"products/{product_id}/releases", allow_404=True)
        return self._handle_list_response(response, "releases")

    def get_actions(self, product_id: int) -> list[dict[str, Any]]:
        """获取产品的操作记录 (Action Logs)。"""
        response = self._get(f"products/{product_id}/actions", allow_404=True)
        return self._handle_list_response(response, "actions")

    def get_tasks(self, execution_id: int) -> list[dict[str, Any]]:
        """获取执行 (迭代) 下的任务。"""
        response = self._get(f"executions/{execution_id}/tasks", allow_404=True)
        return self._handle_list_response(response, "tasks")

    def get_departments(self) -> list[dict[str, Any]]:
        """获取组织架构部门列表。"""
        response = self._get("departments", allow_404=True)
        return self._handle_list_response(response, "departments")

    def get_users(self) -> list[dict[str, Any]]:
        """获取用户列表。"""
        response = self._get("users", allow_404=True)
        return self._handle_list_response(response, "users")

"""Nexus Repository OSS API 客户端"""

import base64
from collections.abc import Generator

from devops_collector.core.base_client import BaseClient


class NexusClient(BaseClient):
    """Nexus Repository v3 REST API 客户端。"""

    def __init__(self, url: str, user: str, password: str, rate_limit: int = 10):
        '''"""TODO: Add description.

        Args:
            self: TODO
            url: TODO
            user: TODO
            password: TODO
            rate_limit: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        auth_str = f"{user}:{password}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()
        super().__init__(
            base_url=f"{url.rstrip('/')}/service/rest/v1",
            auth_headers={"Authorization": f"Basic {encoded_auth}", "Accept": "application/json"},
            rate_limit=rate_limit,
        )

    def test_connection(self) -> bool:
        """测试连接。"""
        try:
            self._get("status/check")
            return True
        except Exception:
            return False

    def list_repositories(self) -> list[dict]:
        """获取仓库列表。"""
        return self._get("repositories").json()

    def list_components(self, repository: str) -> Generator[dict, None, None]:
        """流式获取仓库下的组件列表（支持自动分页）。"""
        continuation_token = None
        while True:
            params = {"repository": repository}
            if continuation_token:
                params["continuationToken"] = continuation_token
            response = self._get("components", params=params).json()
            items = response.get("items", [])
            yield from items
            continuation_token = response.get("continuationToken")
            if not continuation_token:
                break

    def get_component(self, component_id: str) -> dict:
        """获取特定组件详情。"""
        return self._get(f"components/{component_id}").json()

    def list_assets(self, repository: str) -> Generator[dict, None, None]:
        """流式获取资产列表。"""
        continuation_token = None
        while True:
            params = {"repository": repository}
            if continuation_token:
                params["continuationToken"] = continuation_token
            response = self._get("assets", params=params).json()
            items = response.get("items", [])
            yield from items
            continuation_token = response.get("continuationToken")
            if not continuation_token:
                break

    def download_asset_content(self, download_url: str) -> str:
        """下载资产内容（通常用于解析小型元数据文件）。"""
        response = self._get(download_url, is_full_url=True)
        return response.text

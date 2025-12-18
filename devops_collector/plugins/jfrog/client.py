"""JFrog Artifactory API 客户端"""
from typing import List, Dict, Optional, Any, Generator
from devops_collector.core.base_client import BaseClient

class JFrogClient(BaseClient):
    """JFrog Artifactory REST API 客户端。"""
    
    def __init__(self, url: str, token: str, rate_limit: int = 10):
        super().__init__(
            base_url=f"{url.rstrip('/')}/artifactory/api",
            auth_headers={'Authorization': f'Bearer {token}'},
            rate_limit=rate_limit
        )

    def test_connection(self) -> bool:
        """测试连接。"""
        try:
            self._get("system/ping")
            return True
        except Exception:
            return False

    def get_artifacts(self, repo: str, path: str = "") -> Generator[Dict, None, None]:
        """通过 AQL 或递归 API 获取仓库下的制品列表。"""
        # 示例：使用 AQL 进行高效查询
        endpoint = "search/aql"
        query = f'items.find({{"repo": "{repo}", "path": {{"$match": "{path}*"}}, "type": "file"}}).include("*", "property")'
        
        response = self._post(endpoint, data=query, headers={'Content-Type': 'text/plain'})
        data = response.json()
        
        for item in data.get('results', []):
            yield item

    def get_artifact_stats(self, repo: str, path: str) -> Dict:
        """获取制品的下载量等统计信息。"""
        return self._get(f"storage/{repo}/{path}?stats").json()

    def get_build_info(self, build_name: str, build_number: str) -> Dict:
        """获取构建详细信息。"""
        # 注意：构建信息 API 通常在 /artifactory/api/build/ 下
        return self._get(f"build/{build_name}/{build_number}").json()

    def get_xray_summary(self, repo: str, path: str) -> Dict:
        """从 Xray 获取安全漏洞摘要。"""
        # 这里可能需要调用 Xray 的独立 API，取决于 JFrog 版本和集成方式
        # 通常可通过存储 API 的特定子路径获取
        try:
            return self._get(f"xray/summary/artifact/{repo}/{path}").json()
        except:
            return {}

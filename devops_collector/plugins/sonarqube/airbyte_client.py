"""PyAirbyte SonarQube 调用封装。

本模块提供对 PyAirbyte 库的封装，支持通过 'source-sonarqube' 连接器提取代码质量数据。
"""

import logging
from typing import Any, Dict, Optional, Generator
import airbyte as ab
from devops_collector.core.base_client import BaseClient

logger = logging.getLogger(__name__)

class AirbyteSonarQubeClient(BaseClient):
    """基于 PyAirbyte 的 SonarQube 客户端适配器。
    
    该客户端通过封装 'source-sonarqube' 连接器，提供流式数据获取能力，
    消除了手动处理分页和复杂 API 结构的成本。
    """

    def __init__(self, url: str, token: str):
        """初始化 PyAirbyte SonarQube 客户端。
        
        Args:
            url (str): SonarQube 实例 URL。
            token (str): 认证 Token。
        """
        super().__init__(base_url=url, auth_headers={'Authorization': f'Bearer {token}'})
        
        # Airbyte SonarQube Connector Config
        # 根据官方文档：https://docs.airbyte.com/integrations/sources/sonarqube
        self.source_config = {
            "host_url": url.rstrip('/'),
            "credentials": {
                "auth_type": "user_token",
                "user_token": token
            }
        }
        self._source: Optional[ab.Source] = None

    @property
    def source(self) -> ab.Source:
        """获取或初始化 Airbyte Source 实例。"""
        if self._source is None:
            logger.info("正在初始化 PyAirbyte 'source-sonarqube' 连接器...")
            self._source = ab.get_source("source-sonarqube", config=self.source_config)
        return self._source

    def test_connection(self) -> bool:
        """测试连接可用性。"""
        try:
            return self.source.check().status == "SUCCEEDED"
        except Exception as e:
            logger.error(f"PyAirbyte SonarQube connection check failed: {e}")
            return False

    def get_stream_records(self, stream_name: str) -> Generator[Dict[str, Any], None, None]:
        """流式获取指定 stream 的原始记录。
        
        Available streams usually include: projects, issues, components, measures.
        """
        logger.info(f"正在从 SonarQube 流 '{stream_name}' 读取数据...")
        self.source.select_streams([stream_name])
        read_result = self.source.read()
        
        for record in read_result[stream_name]:
            yield record.to_dict()

    # --- 兼容旧接口的适配逻辑 ---
    
    def get_all_projects(self) -> list:
        """兼容接口：获取所有项目。"""
        return list(self.get_stream_records("projects"))

    def get_project(self, key: str) -> Optional[dict]:
        """兼容接口：获取单个项目。"""
        for p in self.get_stream_records("projects"):
            if p.get("key") == key:
                return p
        return None

    def get_measures(self, project_key: str) -> Dict[str, Any]:
        """兼容接口：获取项目指标。"""
        # 注意：Airbyte 的 measures 流通常包含历史或详细数据，需按需聚合
        # 此处简化为获取该项目关联的记录
        measures = {}
        for m in self.get_stream_records("measures"):
            if m.get("componentKey") == project_key:
                measures[m["metric"]] = m.get("value")
        return measures

    def get_quality_gate_status(self, project_key: str) -> dict:
        """兼容接口：获取质量门禁。"""
        # Airbyte 暂不一定直接支持该原子 API，若不支持可 fallback 或从 measures 流提取
        for m in self.get_stream_records("measures"):
            if m.get("componentKey") == project_key and m.get("metric") == "alert_status":
                return {"status": m.get("value")}
        return {"status": "UNKNOWN"}

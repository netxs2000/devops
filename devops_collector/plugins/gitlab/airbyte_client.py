"""PyAirbyte 调用封装。

本模块提供对 PyAirbyte 库的二次封装，使其适配现有的 BaseClient 接口风格，
方便在 Worker 中透明切换。
"""

import logging
from typing import Any, Dict, Optional, Generator
import airbyte as ab
from devops_collector.core.base_client import BaseClient

logger = logging.getLogger(__name__)

class AirbyteGitLabClient(BaseClient):
    """基于 PyAirbyte 的 GitLab 客户端适配器。
    
    该客户端通过封装 'source-gitlab' 连接器，提供流式数据获取能力，
    无需手动处理分页、速率限制和 API 映射。
    """

    def __init__(self, url: str, token: str, start_date: str = "2024-01-01T00:00:00Z"):
        """初始化 PyAirbyte GitLab 客户端。
        
        Args:
            url (str): GitLab 实例 URL。
            token (str): Private Token 或 Access Token。
            start_date (str): 增量同步的最早起始时间。
        """
        # 调用父类初始化，虽然底层主要由 airbyte 库处理，但保留基类结构以兼容 BaseWorker
        super().__init__(base_url=url, auth_headers={'PRIVATE-TOKEN': token})
        
        self.source_config = {
            "api_url": url,
            "credentials": {
                "auth_type": "access_token",
                "access_token": token
            },
            "start_date": start_date
        }
        self._source: Optional[ab.Source] = None

    @property
    def source(self) -> ab.Source:
        """获取或初始化 Airbyte Source 实例。"""
        if self._source is None:
            logger.info("正在初始化 PyAirbyte 'source-gitlab' 连接器...")
            self._source = ab.get_source("source-gitlab", config=self.source_config)
        return self._source

    def test_connection(self) -> bool:
        """测试连接可用性。"""
        try:
            return self.source.check().status == "SUCCEEDED"
        except Exception as e:
            logger.error(f"PyAirbyte GitLab connection check failed: {e}")
            return False

    def get_stream_records(self, stream_name: str, project_ids: Optional[list] = None) -> Generator[Dict[str, Any], None, None]:
        """流式获取指定 stream 的原始记录。
        
        Args:
            stream_name (str): Airbyte 数据流名称 (如 'commits', 'issues', 'merge_requests')。
            project_ids (list): 可选，过滤特定的项目 ID 列表。
            
        Yields:
            Generator[Dict[str, Any]]: 原始记录字典生成器。
        """
        # 如果需要过滤项目，Airbyte GitLab 连接器通常在配置中指定 projects 或 groups
        # 这里的实现支持全量流式读取
        logger.info(f"正在从流 '{stream_name}' 读取数据...")
        self.source.select_streams([stream_name])
        read_result = self.source.read()
        
        for record in read_result[stream_name]:
            yield record.to_dict()

    # 兼容旧接口的 mock 方法，用于最小化修改原有 Mixins
    def get_project_commits(self, project_id: int, since: Optional[str] = None) -> Generator[Dict, None, None]:
        """兼容接口：获取项目提交。"""
        # 注意：此处为演示逻辑，Airbyte 通常一次拉取配置范围内的所有项目
        for record in self.get_stream_records("commits"):
            if str(record.get("project_id")) == str(project_id):
                yield record

    def get_project_issues(self, project_id: int, since: Optional[str] = None) -> Generator[Dict, None, None]:
        """兼容接口：获取项目 Issue。"""
        for record in self.get_stream_records("issues"):
            if str(record.get("project_id")) == str(project_id):
                yield record

    def get_project_merge_requests(self, project_id: int, since: Optional[str] = None) -> Generator[Dict, None, None]:
        """兼容接口：获取项目 MR。"""
        for record in self.get_stream_records("merge_requests"):
            if str(record.get("project_id")) == str(project_id):
                yield record

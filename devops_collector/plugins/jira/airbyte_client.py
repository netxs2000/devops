"""PyAirbyte Jira 客户端适配器

本模块提供对 PyAirbyte 库的封装，支持通过 'source-jira' 连接器提取数据，
并适配现有的 JiraClient 接口风格。
"""
import logging
import re
import airbyte as ab
from urllib.parse import urlparse
from typing import List, Dict, Optional, Any
from devops_collector.core.base_client import BaseClient

logger = logging.getLogger(__name__)

class AirbyteJiraClient(BaseClient):
    """基于 PyAirbyte 的 Jira 客户端适配器。"""

    def __init__(self, url: str, email: str, api_token: str, rate_limit: int = 5) -> None:
        """初始化 PyAirbyte Jira 客户端。
        
        Args:
            url (str): Jira 实例地址 (如 https://your-domain.atlassian.net)。
            email (str): 用户邮箱。
            api_token (str): API 令牌。
            rate_limit (int): 忽略。
        """
        super().__init__(base_url=url, rate_limit=rate_limit)
        
        # 提取域名
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        self.config = {
            "domain": domain,
            "email": email,
            "api_token": api_token
        }
        
        self._source = None
        self._cache: Dict[str, List[dict]] = {}

    def _get_source(self):
        """获取或初始化 Airbyte Source 实例。"""
        if self._source:
            return self._source
            
        logger.info("正在初始化 PyAirbyte 'source-jira' 连接器...")
        try:
            self._source = ab.get_source(
                "source-jira",
                config=self.config,
                install_if_missing=True
            )
            self._source.check()
            return self._source
        except Exception as e:
            logger.error(f"PyAirbyte Jira connection check failed: {e}")
            raise

    def _load_stream(self, stream_name: str) -> List[dict]:
        """加载并缓存指定流的数据。"""
        if stream_name in self._cache:
            return self._cache[stream_name]
            
        source = self._get_source()
        logger.info(f"Reading '{stream_name}' stream from Airbyte...")
        
        # 处理可能的流名称不一致问题，Airbyte流名称通常是复数
        available_streams = source.get_available_streams()
        target_stream = stream_name
        if stream_name not in available_streams and stream_name + 's' in available_streams:
             target_stream = stream_name + 's'
        elif stream_name == 'projects':
             # specific check if needed
             pass

        try:
            source.select_streams([target_stream])
            result = source.read()
            data = []
            for record in result.streams[target_stream]:
                data.append(record.to_dict() if hasattr(record, 'to_dict') else record)
            
            logger.info(f"Loaded {len(data)} records for stream '{stream_name}'.")
            self._cache[stream_name] = data
            return data
        except Exception as e:
            logger.warning(f"Failed to load stream '{stream_name}': {e}. Returning empty list.")
            self._cache[stream_name] = []
            return []

    def test_connection(self) -> bool:
        """测试连接。"""
        try:
            self._get_source()
            return True
        except Exception:
            return False

    def get_projects(self) -> List[Dict[str, Any]]:
        """获取所有项目。"""
        return self._load_stream('projects')

    def get_groups(self) -> List[Dict[str, Any]]:
        """获取用户组列表 (对应 Airbyte 'groups' 流)。"""
        # 注意: 具体流名称取决于 source-jira 版本，通常是 'groups' 或 'user_groups'
        # 尝试加载 groups
        return self._load_stream('groups')

    def get_all_users(self) -> List[Dict[str, Any]]:
        """获取所有用户 (对应 Airbyte 'users' 流)。"""
        return self._load_stream('users')

    def get_boards(self, project_key: Optional[str]=None) -> List[Dict[str, Any]]:
        """获取看板。"""
        # source-jira 的 boards 流可能不可用或结构不同。
        # 假设存在 'boards' 流
        boards = self._load_stream('boards')
        if not project_key:
            return boards
            
        filtered_boards = []
        for board in boards:
            # 检查 board location
            # 结构示例: location: {projectKey: 'KEY', ...}
            loc = board.get('location', {})
            if loc and loc.get('projectKey') == project_key:
                filtered_boards.append(board)
        return filtered_boards

    def get_sprints(self, board_id: int) -> List[Dict[str, Any]]:
        """获取看板下的 Sprints。"""
        # 假设存在 'sprints' 流
        sprints = self._load_stream('sprints')
        return [s for s in sprints if s.get('originBoardId') == board_id or s.get('originBoardId') == str(board_id)]

    def get_issues(self, jql: str) -> List[Dict[str, Any]]:
        """获取 Issues。注意：Airbyte 不支持 JQL 查询，这里使用缓存过滤。"""
        all_issues = self._load_stream('issues')
        
        # 简单的 JQL 解析：仅提取 `project = KEY`
        # 如果 JQL 复杂，这里的过滤可能不准确，建议 Worker 进一步验证
        # 假设 JQL 格式为 "project = KEY" 或 "project=KEY"
        project_key = None
        match = re.search(r"project\s*=\s*['\"]?(\w+)['\"]?", jql, re.IGNORECASE)
        if match:
            project_key = match.group(1)
            
        if not project_key:
            logger.warning(f"Could not parse Project Key from JQL: '{jql}'. Returning all cached issues (may be mixed projects).")
            return all_issues
            
        filtered = []
        for issue in all_issues:
            # issue fields 包含 project: {key: 'KEY'}
            p = issue.get('fields', {}).get('project', {})
            if p.get('key') == project_key:
                filtered.append(issue)
        return filtered

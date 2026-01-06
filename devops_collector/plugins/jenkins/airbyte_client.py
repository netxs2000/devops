"""PyAirbyte Jenkins 客户端适配器

本模块提供对 PyAirbyte 库的封装，支持通过 'source-jenkins' 连接器提取数据，
并适配现有的 JenkinsClient 接口风格。
"""
import logging
import airbyte as ab
from typing import List, Dict, Optional, Any
from devops_collector.core.base_client import BaseClient

logger = logging.getLogger(__name__)

class AirbyteJenkinsClient(BaseClient):
    """基于 PyAirbyte 的 Jenkins 客户端适配器。"""

    def __init__(self, url: str, user: str, token: str, rate_limit: int = 10) -> None:
        """初始化 PyAirbyte Jenkins 客户端。
        
        Args:
            url (str): Jenkins 实例地址。
            user (str): Jenkins 用户名。
            token (str): Jenkins API Token。
            rate_limit (int): 忽略（由 Airbyte 控制）。
        """
        # 调用父类初始化，保留结构兼容
        super().__init__(base_url=url, rate_limit=rate_limit)
        
        self.config = {
            "server_url": url,
            "username": user,
            "api_token": token
        }
        self._source = None
        self._jobs_cache: Optional[List[dict]] = None
        self._builds_cache: Dict[str, List[dict]] = {} # job_full_name -> list of build summaries
        self._build_details_map: Dict[str, dict] = {} # url -> build details
        
    def _get_source(self):
        """获取或初始化 Airbyte Source 实例。"""
        if self._source:
            return self._source
            
        logger.info("正在初始化 PyAirbyte 'source-jenkins' 连接器...")
        try:
            self._source = ab.get_source(
                "source-jenkins",
                config=self.config,
                install_if_missing=True
            )
            self._source.check()
            return self._source
        except Exception as e:
            logger.error(f"PyAirbyte Jenkins connection check failed: {e}")
            raise

    def _ensure_jobs_loaded(self):
        """按需加载 Job 数据。"""
        if self._jobs_cache is not None:
            return
            
        source = self._get_source()
        logger.info("Reading 'jobs' stream from Airbyte...")
        source.select_streams(["jobs"])
        result = source.read()
        
        self._jobs_cache = []
        for record in result.streams["jobs"]:
            # 适配 Jenkins API 返回格式
            # Airbyte 记录通常包含: name, url, color, description 等
            job_data = record.to_dict() if hasattr(record, 'to_dict') else record
            # 确保 fullName 存在 (Airbyte 可能用 different field name, 假设 mapping 兼容)
            if 'fullName' not in job_data:
                job_data['fullName'] = job_data.get('name') 
            self._jobs_cache.append(job_data)
        logger.info(f"Loaded {len(self._jobs_cache)} jobs from Airbyte.")

    def _ensure_builds_loaded(self):
        """按需加载 Build 数据。"""
        if self._build_details_map:
            return
            
        source = self._get_source()
        logger.info("Reading 'builds' stream from Airbyte...")
        source.select_streams(["builds"])
        result = source.read()
        
        count = 0
        for record in result.streams["builds"]:
            build_data = record.to_dict() if hasattr(record, 'to_dict') else record
            url = build_data.get('url')
            if not url:
                continue
                
            self._build_details_map[url] = build_data
            
            # 尝试从 URL 解析 Job Name，或者 Airbyte 记录里有 Project 字段
            # Jenkins Build URL format: .../job/FOLDER/job/NAME/NUMBER/
            # 这是一个简化的提取逻辑，真正稳健的逻辑需要解析 URL 结构
            # 假设 record 中有 'job_name' 或类似字段会更好，但保守起见我们不做过多假设
            # 这里我们简单地遍历 _jobs_cache 来匹配？太慢。
            # 为了适配 get_builds(job_full_name)，我们需要建立索引。
            
            # 这里的 Hack: 我们假设调用 get_builds 时传入的 job_full_name 能在 build 记录里找到线索
            # 暂时我们将所有 build 都放在缓存里，但在 get_builds 里过滤
            pass
            count += 1
        logger.info(f"Loaded {count} builds from Airbyte.")

    def get_jobs(self, folder: Optional[str]=None) -> List[dict]:
        """获取 Job 列表。"""
        self._ensure_jobs_loaded()
        # 简单过滤：如果 folder 为 None，返回所有；否则过滤 (MVP 实现)
        # 注意：BaseClient 的 folder 参数逻辑是只返回该层级。
        # 这里返回全量，Worker 里的递归逻辑可能需要调整，但在 sync_all_jobs 模式下通常只调一次 get_jobs()
        return self._jobs_cache

    def get_builds(self, job_full_name: str, limit: int=100) -> List[dict]:
        """获取指定 Job 的构建列表。"""
        self._ensure_builds_loaded()
        
        # 从缓存中筛选属于 job_full_name 的 builds
        # 这是一个 O(N) 操作，如果构建数万可能较慢。
        candidates = []
        for url, data in self._build_details_map.items():
            # 检查 URL 是否包含 job_full_name
            # e.g. /job/my-job/1/
            if f"/job/{job_full_name}/" in url or f"/{job_full_name}/" in url:
                candidates.append({
                    'number': data.get('number'),
                    'url': url
                })
        
        # 按 number 倒序
        candidates.sort(key=lambda x: int(x['number']), reverse=True)
        return candidates[:limit]

    def get_build_details(self, build_url: str) -> Dict[str, Any]:
        """获取构建详情。"""
        self._ensure_builds_loaded()
        return self._build_details_map.get(build_url, {})

    def get_test_report(self, build_url: str) -> Optional[Dict[str, Any]]:
        """获取测试报告（Airbyte 可能不支持，返回 None）。"""
        # Airbyte 基础 Connector 通常不爬取 testReport/api/json
        # 如果需要，这里可以回退到使用 requests 直接访问
        return None

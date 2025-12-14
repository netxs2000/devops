"""API 客户端抽象基类模块

提供所有数据源客户端的通用功能：
- 令牌桶速率限制
- 指数退避自动重试
- 统一的认证管理

Typical usage:
    class MyClient(BaseClient):
        def test_connection(self) -> bool:
            return self._get("health").ok
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class RateLimiter:
    """令牌桶算法实现的速率限制器。
    
    确保 API 调用频率不超过目标系统限制，避免 429 错误。
    
    Args:
        rate_limit: 每秒允许的请求数
    
    Example:
        limiter = RateLimiter(10)  # 10 次/秒
        limiter.wait_for_token()   # 阻塞直到可以发送请求
    """
    
    def __init__(self, rate_limit: int = 10):
        self.rate_limit = rate_limit
        self.tokens = float(rate_limit)
        self.last_update = time.time()

    def get_token(self) -> bool:
        """尝试获取一个请求令牌。
        
        Returns:
            True 如果成功获取令牌，False 如果需要等待
        """
        current = time.time()
        time_passed = current - self.last_update
        self.tokens += time_passed * self.rate_limit
        if self.tokens > self.rate_limit:
            self.tokens = float(self.rate_limit)
        self.last_update = current

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        else:
            return False

    def wait_for_token(self) -> None:
        """阻塞等待直到获取到令牌。"""
        while not self.get_token():
            time.sleep(0.1)


class BaseClient(ABC):
    """所有数据源客户端的抽象基类。
    
    提供统一的 HTTP 请求接口，包含：
    - 速率限制
    - 自动重试 (指数退避)
    - 认证头管理
    - 超时控制
    
    Attributes:
        base_url: API 基础地址
        headers: 包含认证信息的请求头
        limiter: 速率限制器实例
        timeout: 请求超时时间 (秒)
    
    Example:
        class GitLabClient(BaseClient):
            def __init__(self, url, token):
                super().__init__(
                    base_url=f"{url}/api/v4",
                    auth_headers={'PRIVATE-TOKEN': token}
                )
            
            def test_connection(self) -> bool:
                return self._get("version").ok
    """
    
    def __init__(
        self, 
        base_url: str, 
        auth_headers: Dict[str, str],
        rate_limit: int = 10,
        timeout: int = 30,
        max_retries: int = 5
    ):
        """初始化客户端。
        
        Args:
            base_url: API 基础地址 (不含尾部斜杠)
            auth_headers: 认证头信息
            rate_limit: 每秒请求上限
            timeout: 请求超时时间 (秒)
            max_retries: 最大重试次数
        """
        self.base_url = base_url.rstrip('/')
        self.headers = auth_headers
        self.limiter = RateLimiter(rate_limit)
        self.timeout = timeout
        self.max_retries = max_retries
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((requests.exceptions.RequestException,))
    )
    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """发送 GET 请求。
        
        Args:
            endpoint: API 端点 (相对路径)
            params: 查询参数
            
        Returns:
            Response 对象
            
        Raises:
            requests.exceptions.HTTPError: 4xx/5xx 错误
            requests.exceptions.RequestException: 网络错误
        """
        self.limiter.wait_for_token()
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params, 
                timeout=self.timeout
            )
            
            # 处理速率限制
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Sleeping for {retry_after}s")
                time.sleep(retry_after)
                raise requests.exceptions.RequestException("Rate Limited")
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403]:
                logger.error(f"Auth error: {e}")
                raise  # 不重试认证错误
            raise
    
    def _post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """发送 POST 请求。
        
        Args:
            endpoint: API 端点
            data: 请求体数据
            
        Returns:
            Response 对象
        """
        self.limiter.wait_for_token()
        url = f"{self.base_url}/{endpoint}"
        
        response = requests.post(
            url, 
            headers=self.headers, 
            json=data, 
            timeout=self.timeout
        )
        response.raise_for_status()
        return response
    
    @abstractmethod
    def test_connection(self) -> bool:
        """测试与目标系统的连接是否正常。
        
        Returns:
            True 如果连接正常，False 否则
        """
        pass

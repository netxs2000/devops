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

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


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
        """初始化速率限制器。

        Args:
            rate_limit (int): 每秒允许的请求数 (TPS)。
        """
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


def is_retryable_exception(exception: Exception) -> bool:
    """判断异常是否值得重试。

    401 (Unauthorized) 和 403 (Forbidden) 通常表示配置错误，重试无意义。
    """
    if isinstance(exception, requests.exceptions.HTTPError):
        if exception.response.status_code in [401, 403]:
            return False
    from devops_collector.core.exceptions import CircuitBreakerOpenError

    if isinstance(exception, CircuitBreakerOpenError):
        return False
    return isinstance(exception, requests.exceptions.RequestException)


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
        auth_headers: dict[str, str],
        rate_limit: int = 10,
        timeout: int = 30,
        max_retries: int = 5,
        verify: bool = True,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        """初始化客户端。"""
        self.base_url = base_url.rstrip("/")
        self.headers = auth_headers
        self.limiter = RateLimiter(rate_limit)
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify = verify

        # 熔断器状态
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "CLOSED"  # CLOSED, OPEN

        # 19.6 资源池化：使用 Session 复用 TCP 连接
        self._session = requests.Session()
        self._session.headers.update(self.headers)
        self._session.verify = self.verify

    def _mask_headers(self, headers: dict) -> dict:
        """19.8 日志脱敏：遮蔽请求头中的敏感令牌。"""
        mask_keys = {"Authorization", "PRIVATE-TOKEN", "Token", "X-Auth-Token"}
        return {k: ("******" if k in mask_keys else v) for k, v in headers.items()}

    def _check_circuit(self) -> None:
        """核心熔断判定。"""
        if self._state == "OPEN":
            if time.time() - self._last_failure_time > self.recovery_timeout:
                logger.info(f"[{self.__class__.__name__}] Circuit [HALF_OPEN] - Probe attempt.")
            else:
                from devops_collector.core.exceptions import CircuitBreakerOpenError

                raise CircuitBreakerOpenError(f"Circuit Breaker for {self.__class__.__name__} is OPEN.")

    def _handle_failure(self, error: Exception) -> None:
        """记录失败并触发熔断。"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            if self._state != "OPEN":
                logger.critical(f"[{self.__class__.__name__}] Circuit OPEN! Caused by: {error}")
                self._state = "OPEN"

    def _handle_success(self) -> None:
        """重置熔断状态。"""
        if self._state != "CLOSED":
            logger.info(f"[{self.__class__.__name__}] Circuit recovered to CLOSED.")
        self._failure_count = 0
        self._state = "CLOSED"

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception(is_retryable_exception),
        reraise=True,
    )
    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> requests.Response:
        """发送 GET 请求。"""
        self._check_circuit()
        self.limiter.wait_for_token()
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited. Sleeping for {retry_after}s")
                time.sleep(retry_after)
                raise requests.exceptions.RequestException("Rate Limited")
            response.raise_for_status()
            self._handle_success()
            return response
        except (requests.exceptions.RequestException, ConnectionError) as e:
            masked_headers = self._mask_headers(self.headers)
            logger.error(f"Network error on {endpoint} with headers {masked_headers}: {e}")
            self._handle_failure(e)
            raise
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403]:
                masked_headers = self._mask_headers(self.headers)
                logger.error(f"Auth error (401/403) on {endpoint} with headers {masked_headers}")
                raise
            raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception(is_retryable_exception),
        reraise=True,
    )
    def _post(
        self,
        endpoint: str,
        data: Any | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        """发送 POST 请求。"""
        self._check_circuit()
        self.limiter.wait_for_token()
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self._session.post(url, data=data, json=json, timeout=self.timeout, headers=headers)
            response.raise_for_status()
            self._handle_success()
            return response
        except (requests.exceptions.RequestException, ConnectionError) as e:
            self._handle_failure(e)
            raise
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403]:
                masked_headers = self._mask_headers(self.headers)
                logger.error(f"Auth error on POST {endpoint} with headers {masked_headers}")
                raise
            raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception(is_retryable_exception),
    )
    def _put(self, endpoint: str, data: dict[str, Any] | None = None) -> requests.Response:
        """发送 PUT 请求。"""
        self._check_circuit()
        self.limiter.wait_for_token()
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self._session.put(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            self._handle_success()
            return response
        except (requests.exceptions.RequestException, ConnectionError) as e:
            self._handle_failure(e)
            raise
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403]:
                masked_headers = self._mask_headers(self.headers)
                logger.error(f"Auth error on PUT {endpoint} with headers {masked_headers}")
                raise
            raise

    @abstractmethod
    def test_connection(self) -> bool:
        """测试与目标系统的连接是否正常。

        Returns:
            True 如果连接正常，False 否则
        """
        pass

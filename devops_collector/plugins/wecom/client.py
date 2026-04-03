"""企业微信 (WeCom) API 客户端

实现 Access Token 缓存管理、部门树拉取、成员详情获取。
遵循 contexts.md 17.2 节 MDM 金科玉律中的"隔离暂存区"原则——
Client 仅负责 API 通信，不执行任何数据库操作。
"""

import logging
import time

import requests

from devops_collector.core.base_client import BaseClient
from devops_collector.core.exceptions import CircuitBreakerOpenError


logger = logging.getLogger(__name__)


class WeComClient(BaseClient):
    """企业微信通讯录 API 客户端。

    职责边界：仅负责 HTTP 通信与 Token 管理。
    继承自 BaseClient，自动获得熔断、限流与指数退避重试能力。
    """

    def __init__(
        self,
        corp_id: str,
        secret: str,
        verify_ssl: bool = True,
        rate_limit: int = 10,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        """初始化企业微信客户端。"""
        super().__init__(
            base_url="https://qyapi.weixin.qq.com/cgi-bin",
            auth_headers={},  # WeCom 使用 URL 参数传递 Token，无需 Header 认证
            rate_limit=rate_limit,
            verify=verify_ssl,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
        self.corp_id = corp_id
        self.secret = secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    # ─────────────────────────────────────
    #  Token 管理
    # ─────────────────────────────────────

    def _refresh_token(self) -> None:
        """获取或刷新 Access Token (带缓存，有效期 7200 秒)。"""
        url = f"{self.base_url}/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.secret}
        # 19.6 使用池化 Session 替换原生 requests 调用，确保连接复用
        resp = self._session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode") != 0:
            raise ConnectionError(f"WeChat Token Error: {data.get('errmsg')}")
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 7200) - 300
        logger.info("WeChat Access Token refreshed successfully.")

    @property
    def access_token(self) -> str:
        """获取当前有效的 Access Token (自动刷新)。"""
        if not self._access_token or time.time() >= self._token_expires_at:
            self._refresh_token()
        return self._access_token

    def _get(self, path: str, params: dict | None = None) -> dict:
        """封装 GET 请求，支持 Token 自动重试。"""
        params = params or {}
        params["access_token"] = self.access_token
        endpoint = path.lstrip("/")

        try:
            # 调用基类方法，自动获得熔断与重试保护
            resp = super()._get(endpoint, params=params)
            data = resp.json()

            # 处理 Token 过期 (42001)
            if data.get("errcode") == 42001:
                logger.info("WeCom Token expired (42001), refreshing...")
                self._refresh_token()
                params["access_token"] = self.access_token
                resp = super()._get(endpoint, params=params)
                data = resp.json()

            if data.get("errcode") not in (0, None):
                logger.warning(f"WeChat API Business Error on {path}: {data}")
            return data

        except (CircuitBreakerOpenError, requests.RequestException):
            raise

    # ─────────────────────────────────────
    #  通讯录 - 部门
    # ─────────────────────────────────────

    def get_departments(self) -> list[dict]:
        """获取企业全量部门列表 (平铺结构)。

        Returns:
            部门字典列表，每项包含 id, name, parentid, order 等字段。
        """
        data = self._get("/department/list")
        departments = data.get("department", [])
        logger.info(f"Fetched {len(departments)} departments from WeCom.")
        return departments

    def get_department_detail(self, dept_id: int) -> dict | None:
        """获取单个部门的详情 (含负责人信息)。"""
        data = self._get("/department/get", {"id": dept_id})
        return data.get("department")

    # ─────────────────────────────────────
    #  通讯录 - 成员
    # ─────────────────────────────────────

    def get_department_users(self, dept_id: int) -> list[dict]:
        """获取指定部门的全量成员详情列表。

        Args:
            dept_id: 企业微信部门 ID。

        Returns:
            成员字典列表，每项包含 userid, name, email, mobile,
            department (list), position, status 等字段。
        """
        data = self._get("/user/list", {"department_id": dept_id})
        users = data.get("userlist", [])
        return users

    def get_all_users(self) -> list[dict]:
        """拉取全企业用户 (按部门逐级遍历，自动去重)。

        策略：先拉部门树，再按每个叶子节点拉取成员，
        利用 userid 去重避免跨部门兼职人员重复。
        """
        departments = self.get_departments()
        seen_ids: set[str] = set()
        all_users: list[dict] = []

        for dept in departments:
            users = self.get_department_users(dept["id"])
            for u in users:
                uid = u.get("userid", "")
                if uid and uid not in seen_ids:
                    seen_ids.add(uid)
                    all_users.append(u)

        logger.info(f"Fetched {len(all_users)} unique users from WeCom across {len(departments)} departments.")
        return all_users

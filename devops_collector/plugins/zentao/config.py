"""禅道插件配置模块

从环境变量中读取禅道相关配置。
"""

import os
from typing import Any


def get_config() -> dict[str, Any]:
    """获取禅道插件的配置。

    Returns:
        包含 client 和 worker 配置的字典
    """
    # 优先匹配 Pydantic 风格的双下划线环境变量，兼容单下划线
    url = os.getenv("ZENTAO__URL") or os.getenv("ZENTAO_URL", "")
    token = os.getenv("ZENTAO__TOKEN") or os.getenv("ZENTAO_TOKEN", "")
    account = os.getenv("ZENTAO__ACCOUNT") or os.getenv("ZENTAO_ACCOUNT")
    password = os.getenv("ZENTAO__PASSWORD") or os.getenv("ZENTAO_PASSWORD")

    return {
        "client": {
            "url": url,
            "token": token,
            "account": account,
            "password": password,
            "rate_limit": int(os.getenv("REQUESTS_PER_SECOND", "5")),
        },
        "worker": {},
    }

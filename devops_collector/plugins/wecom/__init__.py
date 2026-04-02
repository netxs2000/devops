"""企业微信 (WeCom) 插件包

支持企业微信通讯录数据采集（部门 + 成员）。
本模块在导入时自动完成插件注册。
"""

from devops_collector.core.registry import PluginRegistry

from .client import WeComClient
from .worker import WeComWorker


def get_config() -> dict:
    """返回 WeCom 插件所需的环境变量配置映射。"""
    import os

    return {
        "corp_id": os.getenv("WECOM__CORP_ID", ""),
        "secret": os.getenv("WECOM__SECRET", ""),
        "verify_ssl": os.getenv("WECOM__VERIFY_SSL", "True").lower() in ("true", "1"),
        "excluded_departments": [id.strip() for id in os.getenv("WECOM__EXCLUDED_DEPARTMENTS", "").split(",") if id.strip()],
    }


# 自注册
PluginRegistry.register_client("wecom", WeComClient)
PluginRegistry.register_worker("wecom", WeComWorker)
PluginRegistry.register_config("wecom", get_config)

__all__ = ["WeComClient", "WeComWorker", "get_config"]

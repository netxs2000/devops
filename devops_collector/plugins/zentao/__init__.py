"""禅道插件包

支持禅道 (ZenTao) 数据采集。

本模块在导入时自动完成插件注册。
"""
from devops_collector.core.registry import PluginRegistry

from .client import ZenTaoClient
from .config import get_config
from .worker import ZenTaoWorker


# 自注册
PluginRegistry.register_client('zentao', ZenTaoClient)
PluginRegistry.register_worker('zentao', ZenTaoWorker)
PluginRegistry.register_config('zentao', get_config)

__all__ = ['ZenTaoClient', 'ZenTaoWorker', 'get_config']

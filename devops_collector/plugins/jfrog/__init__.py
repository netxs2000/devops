"""JFrog 插件包

支持 JFrog Artifactory 数据采集。

本模块在导入时自动完成插件注册。
"""
from devops_collector.core.registry import PluginRegistry
from .client import JFrogClient
from .worker import JFrogWorker
from .config import get_config

# 自注册
PluginRegistry.register_client('jfrog', JFrogClient)
PluginRegistry.register_worker('jfrog', JFrogWorker)
PluginRegistry.register_config('jfrog', get_config)

__all__ = ['JFrogClient', 'JFrogWorker', 'get_config']

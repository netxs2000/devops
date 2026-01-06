"""Jira 插件包

支持 Jira 数据采集。

本模块在导入时自动完成插件注册。
"""
import os
from devops_collector.core.registry import PluginRegistry
from .worker import JiraWorker
from .config import get_config

# 动态选择客户端：基于 USE_PYAIRBYTE 环境变量
if os.getenv('USE_PYAIRBYTE', 'false').lower() == 'true':
    from .airbyte_client import AirbyteJiraClient as Client
else:
    from .client import JiraClient as Client

# 自注册
PluginRegistry.register_client('jira', Client)
PluginRegistry.register_worker('jira', JiraWorker)
PluginRegistry.register_config('jira', get_config)

__all__ = ['Client', 'JiraWorker', 'get_config']

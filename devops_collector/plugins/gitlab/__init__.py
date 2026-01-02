"""GitLab 数据采集插件

提供 GitLab API 客户端和数据采集 Worker。
"""
from devops_collector.core.registry import PluginRegistry
from .client import GitLabClient
PluginRegistry.register_client('gitlab', GitLabClient)
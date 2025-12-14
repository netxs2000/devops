"""GitLab 数据采集插件

提供 GitLab API 客户端和数据采集 Worker。
"""
from devops_collector.core.registry import PluginRegistry
from .client import GitLabClient

# Worker 在 worker.py 中自行注册，避免循环导入
# from .worker import GitLabWorker

# 注册客户端
PluginRegistry.register_client('gitlab', GitLabClient)

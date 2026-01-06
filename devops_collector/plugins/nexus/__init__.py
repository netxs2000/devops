"""Nexus 插件包

支持 Nexus Repository OSS 数据采集。

本模块在导入时自动完成插件注册。
"""
from devops_collector.core.registry import PluginRegistry
from .client import NexusClient
from .worker import NexusWorker
from .config import get_config

# 自注册
PluginRegistry.register_client('nexus', NexusClient)
PluginRegistry.register_worker('nexus', NexusWorker)
PluginRegistry.register_config('nexus', get_config)

__all__ = ['NexusClient', 'NexusWorker', 'get_config']

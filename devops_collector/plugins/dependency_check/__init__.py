"""Dependency Check 插件

支持 OWASP Dependency-Check 依赖扫描。

本模块在导入时自动完成插件注册。
"""
from devops_collector.core.registry import PluginRegistry
from .client import DependencyCheckClient
from .worker import DependencyCheckWorker
from .config import get_config

# 自注册
PluginRegistry.register_client('dependency_check', DependencyCheckClient)
PluginRegistry.register_worker('dependency_check', DependencyCheckWorker)
PluginRegistry.register_config('dependency_check', get_config)

__all__ = ['DependencyCheckClient', 'DependencyCheckWorker', 'get_config']
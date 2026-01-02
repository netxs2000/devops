"""DevOps Data Collector Core Package

提供插件化架构的核心抽象类和注册表。
"""
from .base_client import BaseClient, RateLimiter
from .base_worker import BaseWorker
from .registry import PluginRegistry
__all__ = ['BaseClient', 'RateLimiter', 'BaseWorker', 'PluginRegistry']
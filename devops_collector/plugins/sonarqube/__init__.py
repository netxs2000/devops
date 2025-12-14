"""SonarQube 数据采集插件

提供 SonarQube Web API 客户端和数据采集 Worker。
"""
from devops_collector.core.registry import PluginRegistry
from .client import SonarQubeClient
from .models import SonarProject, SonarMeasure, SonarIssue

# Worker 在 worker.py 中自行注册
from . import worker

# 注册客户端
PluginRegistry.register_client('sonarqube', SonarQubeClient)

__all__ = ['SonarQubeClient', 'SonarProject', 'SonarMeasure', 'SonarIssue']

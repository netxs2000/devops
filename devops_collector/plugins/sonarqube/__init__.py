"""SonarQube 数据采集插件

提供 SonarQube Web API 客户端和数据采集 Worker。
"""
from devops_collector.core.registry import PluginRegistry
from .client import SonarQubeClient
from .models import SonarProject, SonarMeasure, SonarIssue
from . import worker
PluginRegistry.register_client('sonarqube', SonarQubeClient)
__all__ = ['SonarQubeClient', 'SonarProject', 'SonarMeasure', 'SonarIssue']
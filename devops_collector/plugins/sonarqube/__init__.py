"""SonarQube 数据采集插件

提供 SonarQube Web API 客户端和数据采集 Worker。

本模块在导入时自动完成插件注册。
"""
import os
from devops_collector.core.registry import PluginRegistry
from .models import SonarProject, SonarMeasure, SonarIssue
from .worker import SonarQubeWorker
from .config import get_config

# 根据环境变量动态选择 Client 实现
if os.getenv('USE_PYAIRBYTE', 'false').lower() == 'true':
    from .airbyte_client import AirbyteSonarQubeClient as Client
else:
    from .client import SonarQubeClient as Client

# 自注册: 客户端、Worker 和配置
PluginRegistry.register_client('sonarqube', Client)
PluginRegistry.register_worker('sonarqube', SonarQubeWorker)
PluginRegistry.register_config('sonarqube', get_config)

__all__ = ['Client', 'SonarQubeWorker', 'get_config']

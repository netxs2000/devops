"""GitLab 数据采集插件

提供 GitLab API 客户端和数据采集 Worker。

本模块在导入时自动完成插件注册。
"""
import os
from devops_collector.core.registry import PluginRegistry
from .worker import GitLabWorker
from .config import get_config

# 根据环境变量动态选择 Client 实现
if os.getenv('USE_PYAIRBYTE', 'false').lower() == 'true':
    from .airbyte_client import AirbyteGitLabClient as Client
else:
    from .client import GitLabClient as Client

# 自注册: 客户端、Worker 和配置
PluginRegistry.register_client('gitlab', Client)
PluginRegistry.register_worker('gitlab', GitLabWorker)
PluginRegistry.register_config('gitlab', get_config)

__all__ = ['Client', 'GitLabWorker', 'get_config']

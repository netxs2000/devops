"""Jenkins 插件包

支持 Jenkins 构建数据的采集。

本模块在导入时自动完成插件注册。
"""
import os
from devops_collector.core.registry import PluginRegistry
from .worker import JenkinsWorker
from .models import JenkinsJob, JenkinsBuild
from .config import get_config

# 动态选择客户端：基于 USE_PYAIRBYTE 环境变量
if os.getenv('USE_PYAIRBYTE', 'false').lower() == 'true':
    from .airbyte_client import AirbyteJenkinsClient as Client
else:
    from .client import JenkinsClient as Client

# 自注册: 客户端、Worker 和配置
PluginRegistry.register_client('jenkins', Client)
PluginRegistry.register_worker('jenkins', JenkinsWorker)
PluginRegistry.register_config('jenkins', get_config)

__all__ = ['Client', 'JenkinsWorker', 'JenkinsJob', 'JenkinsBuild', 'get_config']

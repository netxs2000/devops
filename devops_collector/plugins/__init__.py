"""DevOps Data Collector 插件包

所有可用的数据源插件。

本模块在导入时自动发现并加载所有插件。
每个插件目录必须包含 __init__.py 并在其中完成自注册。

Typical usage:
    # 只需导入 plugins 包即可自动加载所有插件
    from devops_collector import plugins
    
    # 或显式触发加载
    from devops_collector.plugins import load_all_plugins
    load_all_plugins()
"""
import logging
from devops_collector.core.plugin_loader import PluginLoader

logger = logging.getLogger(__name__)


def load_all_plugins():
    """手动触发插件加载（通常不需要，import自动触发）。"""
    return PluginLoader.autodiscover()


# 自动加载所有插件
_loaded_plugins = PluginLoader.autodiscover()
logger.info(f'Auto-loaded {len(_loaded_plugins)} plugins: {_loaded_plugins}')

__all__ = ['load_all_plugins']

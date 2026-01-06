"""插件自动发现与加载模块

实现插件的自动扫描、加载和注册机制。
支持从指定目录自动发现所有可用插件，并完成注册。

Typical usage:
    from devops_collector.core.plugin_loader import PluginLoader
    
    # 自动加载所有插件
    PluginLoader.autodiscover()
    
    # 获取已加载的插件列表
    plugins = PluginLoader.list_loaded_plugins()
"""
import os
import sys
import logging
import importlib
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PluginLoader:
    """插件自动发现与加载器。
    
    负责从插件目录自动扫描并导入所有插件模块。
    每个插件在其 __init__.py 中完成自注册。
    """
    
    _loaded_plugins: List[str] = []
    
    @classmethod
    def autodiscover(cls, plugins_dir: str = None) -> List[str]:
        """自动发现并加载所有插件。
        
        Args:
            plugins_dir: 插件目录的绝对路径，默认为 devops_collector/plugins
            
        Returns:
            成功加载的插件名称列表
            
        Example:
            loaded = PluginLoader.autodiscover()
            # ['gitlab', 'sonarqube', 'jenkins', ...]
        """
        if plugins_dir is None:
            # 默认插件目录
            current_dir = Path(__file__).parent.parent
            plugins_dir = current_dir / 'plugins'
        else:
            plugins_dir = Path(plugins_dir)
        
        if not plugins_dir.exists():
            logger.error(f'Plugins directory not found: {plugins_dir}')
            return []
        
        logger.info(f'Autodiscovering plugins from: {plugins_dir}')
        loaded = []
        
        # 遍历插件目录
        for item in plugins_dir.iterdir():
            if not item.is_dir():
                continue
            
            # 跳过私有目录和 __pycache__
            if item.name.startswith('_') or item.name == '__pycache__':
                continue
            
            # 检查是否有 __init__.py
            init_file = item / '__init__.py'
            if not init_file.exists():
                logger.warning(f'Skip {item.name}: no __init__.py found')
                continue
            
            # 动态导入插件模块
            try:
                plugin_name = item.name
                module_path = f'devops_collector.plugins.{plugin_name}'
                logger.debug(f'Loading plugin: {plugin_name} ({module_path})')
                
                # 导入模块（触发 __init__.py 中的自注册代码）
                importlib.import_module(module_path)
                
                cls._loaded_plugins.append(plugin_name)
                loaded.append(plugin_name)
                logger.info(f'Successfully loaded plugin: {plugin_name}')
                
            except Exception as e:
                logger.error(f'Failed to load plugin {item.name}: {e}', exc_info=True)
                continue
        
        logger.info(f'Autodiscovery completed. Loaded {len(loaded)} plugins: {loaded}')
        return loaded
    
    @classmethod
    def list_loaded_plugins(cls) -> List[str]:
        """返回已加载的插件列表。
        
        Returns:
            插件名称列表
        """
        return cls._loaded_plugins.copy()
    
    @classmethod
    def is_plugin_loaded(cls, plugin_name: str) -> bool:
        """检查指定插件是否已加载。
        
        Args:
            plugin_name: 插件名称 (如 'gitlab')
            
        Returns:
            True 如果已加载，否则 False
        """
        return plugin_name in cls._loaded_plugins
    
    @classmethod
    def reload_plugin(cls, plugin_name: str) -> bool:
        """重新加载指定插件（用于开发调试）。
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            True 如果重载成功，False 否则
        """
        try:
            module_path = f'devops_collector.plugins.{plugin_name}'
            if module_path in sys.modules:
                importlib.reload(sys.modules[module_path])
                logger.info(f'Reloaded plugin: {plugin_name}')
                return True
            else:
                logger.warning(f'Plugin {plugin_name} not loaded yet, importing...')
                importlib.import_module(module_path)
                if plugin_name not in cls._loaded_plugins:
                    cls._loaded_plugins.append(plugin_name)
                return True
        except Exception as e:
            logger.error(f'Failed to reload plugin {plugin_name}: {e}')
            return False
    
    @classmethod
    def load_models(cls) -> None:
        """加载所有已注册插件的数据模型。
        
        这对于 SQLAlchemy 的 create_all 或 Alembic 迁移是必须的，
        确保所有定义在插件中的表都能被 Base.metadata 收集到。
        """
        if not cls._loaded_plugins:
            logger.warning("No plugins loaded yet. Calling autodiscover first.")
            cls.autodiscover()
            
        for plugin_name in cls._loaded_plugins:
            try:
                models_path = f'devops_collector.plugins.{plugin_name}.models'
                # 尝试导入 models 模块
                importlib.import_module(models_path)
                logger.debug(f'Loaded models for plugin: {plugin_name}')
            except ImportError:
                # 插件可能没有 models 模块，这是允许的
                pass
            except Exception as e:
                logger.error(f'Failed to load models for plugin {plugin_name}: {e}')

    @classmethod
    def clear(cls) -> None:
        """清空加载记录（主要用于测试）。"""
        cls._loaded_plugins.clear()

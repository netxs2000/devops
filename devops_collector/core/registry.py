"""插件注册表模块

管理所有数据源插件的注册和发现。
支持动态加载客户端、Worker 类和配置。

Typical usage:
    from devops_collector.core.registry import PluginRegistry
    
    # 注册插件
    PluginRegistry.register_client('gitlab', GitLabClient)
    PluginRegistry.register_worker('gitlab', GitLabWorker)
    PluginRegistry.register_config('gitlab', get_gitlab_config)
    
    # 获取插件
    client_cls = PluginRegistry.get_client('gitlab')
    worker_cls = PluginRegistry.get_worker('gitlab')
    config = PluginRegistry.get_config('gitlab')
"""
import logging
from typing import Dict, Type, Optional, List, Callable, Any
logger = logging.getLogger(__name__)

class PluginRegistry:
    """插件注册表，管理所有数据源插件。
    
    使用类方法实现单例模式，所有方法均为类方法。
    
    支持的插件类型:
    - client: API 客户端类
    - worker: 数据采集 Worker 类
    - config: 配置获取函数
    
    Example:
        # 在插件模块中注册
        from devops_collector.core.registry import PluginRegistry
        PluginRegistry.register_client('gitlab', GitLabClient)
        PluginRegistry.register_config('gitlab', get_config)
        
        # 在主程序中使用
        GitLabClient = PluginRegistry.get_client('gitlab')
        config = PluginRegistry.get_config('gitlab')
        client = GitLabClient(**config['client'])
    """
    _clients: Dict[str, Type] = {}
    _workers: Dict[str, Type] = {}
    _configs: Dict[str, Callable[[], Dict[str, Any]]] = {}

    @classmethod
    def register_client(cls, name: str, client_class: Type) -> None:
        """注册 API 客户端类。
        
        Args:
            name: 数据源名称 (如 'gitlab', 'sonarqube')
            client_class: 客户端类 (继承自 BaseClient)
            
        Raises:
            ValueError: 如果同名插件已注册且实现类不同
        """
        if name in cls._clients:
            existing = cls._clients[name]
            if existing is not client_class:
                raise ValueError(f"Client conflict: '{name}' is already registered by {existing.__name__}")
        
        cls._clients[name] = client_class
        logger.debug(f'Registered client: {name} -> {client_class.__name__}')

    @classmethod
    def register_worker(cls, name: str, worker_class: Type) -> None:
        """注册 Worker 类。
        
        Args:
            name: 数据源名称
            worker_class: Worker 类 (继承自 BaseWorker)
            
        Raises:
            ValueError: 如果同名 Worker 已注册且实现类不同
        """
        if name in cls._workers:
            existing = cls._workers[name]
            if existing is not worker_class:
                raise ValueError(f"Worker conflict: '{name}' is already registered by {existing.__name__}")

        cls._workers[name] = worker_class
        logger.debug(f'Registered worker: {name} -> {worker_class.__name__}')

    @classmethod
    def register_config(cls, name: str, config_getter: Callable[[], Dict[str, Any]]) -> None:
        """注册插件配置获取函数。
        
        Args:
            name: 数据源名称
            config_getter: 返回配置字典的函数，格式为 {'client': {...}, 'worker': {...}}
            
        Raises:
            ValueError: 如果同名配置函数已注册且实现不同
            
        Example:
            def get_gitlab_config():
                return {
                    'client': {'url': '...', 'token': '...'},
                    'worker': {'enable_deep_analysis': True}
                }
            
            PluginRegistry.register_config('gitlab', get_gitlab_config)
        """
        if name in cls._configs:
            existing = cls._configs[name]
            if existing is not config_getter:
                # 尝试获取函数名，处理 lambda 或 partial
                func_name = getattr(existing, '__name__', str(existing))
                raise ValueError(f"Config conflict: '{name}' is already registered by {func_name}")

        cls._configs[name] = config_getter
        logger.debug(f'Registered config: {name}')


    @classmethod
    def get_client(cls, name: str) -> Optional[Type]:
        """获取已注册的客户端类。
        
        Args:
            name: 数据源名称
            
        Returns:
            客户端类，如果未找到则返回 None
        """
        if name not in cls._clients:
            logger.warning(f'Client not found: {name}')
            return None
        return cls._clients[name]

    @classmethod
    def get_worker(cls, name: str) -> Optional[Type]:
        """获取已注册的 Worker 类。
        
        Args:
            name: 数据源名称
            
        Returns:
            Worker 类，如果未找到则返回 None
        """
        if name not in cls._workers:
            logger.warning(f'Worker not found: {name}')
            return None
        return cls._workers[name]

    @classmethod
    def get_config(cls, name: str) -> Optional[Dict[str, Any]]:
        """获取插件配置。
        
        Args:
            name: 数据源名称
            
        Returns:
            配置字典 {'client': {...}, 'worker': {...}}，未找到返回 None
        """
        if name not in cls._configs:
            logger.warning(f'Config not found: {name}')
            return None
        
        # 调用配置获取函数
        try:
            config = cls._configs[name]()
            return config
        except Exception as e:
            logger.error(f'Error getting config for {name}: {e}')
            return None


    @classmethod
    def list_plugins(cls) -> Dict[str, Dict[str, str]]:
        """列出所有已注册的插件。
        
        Returns:
            {
                'gitlab': {'client': 'GitLabClient', 'worker': 'GitLabWorker'},
                'sonarqube': {'client': 'SonarQubeClient', 'worker': 'SonarQubeWorker'}
            }
        """
        all_names = set(cls._clients.keys()) | set(cls._workers.keys())
        result = {}
        for name in all_names:
            result[name] = {'client': cls._clients.get(name, type(None)).__name__, 'worker': cls._workers.get(name, type(None)).__name__}
        return result

    @classmethod
    def list_sources(cls) -> List[str]:
        """列出所有已注册的数据源名称。
        
        Returns:
            数据源名称列表
        """
        return list(set(cls._clients.keys()) | set(cls._workers.keys()))

    @classmethod
    def get_client_instance(cls, name: str, **kwargs) -> Optional[object]:
        """获取并实例化客户端。
        
        Args:
            name: 数据源名称
            **kwargs: 传递给客户端构造函数的命名参数
            
        Returns:
            实例化后的客户端对象，如果未找到类则返回 None
        """
        client_cls = cls.get_client(name)
        if not client_cls:
            return None
        return client_cls(**kwargs)

    @classmethod
    def get_worker_instance(cls, name: str, session: object, client: object, **kwargs) -> Optional[object]:
        """获取并实例化 Worker。
        
        Args:
            name: 数据源名称
            session: 数据库会话
            client: 客户端实例
            **kwargs: 传递给 Worker 构造函数的命名参数
            
        Returns:
            实例化后的 Worker 对象，如果未找到类则返回 None
        """
        worker_cls = cls.get_worker(name)
        if not worker_cls:
            return None
        return worker_cls(session, client, **kwargs)

    @classmethod
    def clear(cls) -> None:
        """清空所有注册 (主要用于测试)。"""
        cls._clients.clear()
        cls._workers.clear()
        cls._configs.clear()

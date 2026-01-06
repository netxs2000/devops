"""JFrog 插件配置模块

从环境变量中读取 JFrog 相关配置。
"""
import os
from typing import Dict, Any


def get_config() -> Dict[str, Any]:
    """获取 JFrog 插件的配置。
    
    Returns:
        包含 client 和 worker 配置的字典
    """
    return {
        'client': {
            'url': os.getenv('JFROG_URL', ''),
            'token': os.getenv('JFROG_TOKEN', ''),
            'rate_limit': int(os.getenv('REQUESTS_PER_SECOND', 10))
        },
        'worker': {}
    }

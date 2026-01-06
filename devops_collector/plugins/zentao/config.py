"""禅道插件配置模块

从环境变量中读取禅道相关配置。
"""
import os
from typing import Dict, Any


def get_config() -> Dict[str, Any]:
    """获取禅道插件的配置。
    
    Returns:
        包含 client 和 worker 配置的字典
    """
    return {
        'client': {
            'url': os.getenv('ZENTAO_URL', ''),
            'token': os.getenv('ZENTAO_TOKEN', ''),
            'rate_limit': int(os.getenv('REQUESTS_PER_SECOND', 5))
        },
        'worker': {}
    }

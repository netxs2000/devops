"""Jenkins 插件配置模块

从环境变量中读取 Jenkins 相关配置。
"""
from typing import Dict, Any


def get_config() -> Dict[str, Any]:
    """获取 Jenkins 插件的配置。
    
    Returns:
        包含 client 和 worker 配置的字典:
        {
            'client': {
                'url': str,
                'token': str,
                'user': str
            },
            'worker': {
                'build_limit': int
            }
        }
    """
    from devops_collector.config import Config
    
    return {
        'client': {
            'url': Config.JENKINS_URL,
            'token': Config.JENKINS_TOKEN,
            'user': Config.JENKINS_USER
        },
        'worker': {
            'build_limit': Config.JENKINS_BUILD_SYNC_LIMIT
        }
    }

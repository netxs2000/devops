"""GitLab 插件配置模块

从环境变量中读取 GitLab 相关配置。
"""
from typing import Dict, Any


def get_config() -> Dict[str, Any]:
    """获取 GitLab 插件的配置。
    
    Returns:
        包含 client 和 worker 配置的字典:
        {
            'client': {
                'url': str,
                'token': str,
                'rate_limit': int
            },
            'worker': {
                'enable_deep_analysis': bool
            }
        }
    """
    from devops_collector.config import Config
    
    return {
        'client': {
            'url': Config.GITLAB_URL,
            'token': Config.GITLAB_TOKEN,
            'rate_limit': Config.REQUESTS_PER_SECOND,
            'verify_ssl': Config.GITLAB_VERIFY_SSL
        },
        'worker': {
            'enable_deep_analysis': Config.ENABLE_DEEP_ANALYSIS
        }
    }

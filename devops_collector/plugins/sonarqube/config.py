"""SonarQube 插件配置模块

从环境变量中读取 SonarQube 相关配置。
"""
from typing import Dict, Any


def get_config() -> Dict[str, Any]:
    """获取 SonarQube 插件的配置。
    
    Returns:
        包含 client 和 worker 配置的字典:
        {
            'client': {
                'url': str,
                'token': str,
                'rate_limit': int
            },
            'worker': {
                'sync_issues': bool
            }
        }
    """
    from devops_collector.config import Config
    
    return {
        'client': {
            'url': Config.SONARQUBE_URL,
            'token': Config.SONARQUBE_TOKEN,
            'rate_limit': Config.REQUESTS_PER_SECOND
        },
        'worker': {
            'sync_issues': Config.SONARQUBE_SYNC_ISSUES
        }
    }

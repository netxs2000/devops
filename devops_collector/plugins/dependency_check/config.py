"""Dependency Check 插件配置模块

从环境变量中读取配置。
"""
import os
from typing import Dict, Any


def get_config() -> Dict[str, Any]:
    """获取 Dependency Check 插件的配置。
    
    Returns:
        包含 client 和 worker 配置的字典
    """
    return {
        'client': {
            'cli_path': os.getenv('DEPENDENCY_CHECK_CLI', 'dependency-check'),
            'timeout': int(os.getenv('DEPENDENCY_CHECK_TIMEOUT', 600))
        },
        'worker': {
            'report_dir': os.getenv('DEPENDENCY_CHECK_REPORT_DIR', '/var/lib/devops/dependency-reports'),
            'keep_reports': os.getenv('DEPENDENCY_CHECK_KEEP_REPORTS', 'true').lower() == 'true',
            'retention_days': int(os.getenv('DEPENDENCY_CHECK_RETENTION_DAYS', 90))
        }
    }

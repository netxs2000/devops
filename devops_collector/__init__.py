"""DevOps Data Collector 主包

多数据源研发效能数据采集服务，支持：
- GitLab: 代码仓库、提交、MR、Issue、流水线等
- SonarQube: 代码质量指标、Bug、漏洞、技术债务

使用方式:
    from devops_collector.plugins import gitlab, sonarqube
    from devops_collector.core import PluginRegistry
    
    # 获取已注册的客户端
    GitLabClient = PluginRegistry.get_client('gitlab')
    SonarQubeClient = PluginRegistry.get_client('sonarqube')
"""
__version__ = '2.0.0'
__author__ = 'DevOps Team'

# 导入核心模块
from . import core
# plugins 按需导入，避免循环依赖
# from . import plugins

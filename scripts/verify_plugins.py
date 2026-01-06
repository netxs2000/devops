"""验证插件架构去中心化是否成功

脚本功能：
1. 触发插件自动发现
2. 检查所有预期插件是否已加载
3. 验证 Client、Worker 和 Config 是否都已注册
4. 尝试获取每个插件的配置并打印摘要
"""
import sys
import os
import logging

# 添加项目根目录到 pythonpath
sys.path.append(os.getcwd())

from devops_collector.core.plugin_loader import PluginLoader
from devops_collector.core.registry import PluginRegistry
from devops_collector.plugins import load_all_plugins

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('PluginVerifier')

def main():
    logger.info("Starting Plugin Architecture Verification...")

    # 1. 触发自动发现
    logger.info("1. Triggering Plugin Autodiscovery...")
    # 也可以通过 import devops_collector.plugins 触发，这里显示调用是为了验证 loader
    loaded_plugins = load_all_plugins()
    logger.info(f"   Autodiscovered plugins: {loaded_plugins}")

    expected_plugins = [
        'gitlab', 'sonarqube', 'jenkins', 
        'jira', 'zentao', 'jfrog', 
        'nexus', 'dependency_check'
    ]

    # 2. 验证插件注册状态
    logger.info("\n2. Verifying Plugin Registration Status...")
    all_passed = True
    
    for name in expected_plugins:
        logger.info(f"   Checking plugin: [{name}]")
        
        # 检查加载状态
        if name not in loaded_plugins:
            logger.error(f"   [X] Plugin module '{name}' was not loaded by PluginLoader!")
            all_passed = False
            continue
            
        # 检查组件注册
        client_cls = PluginRegistry.get_client(name)
        worker_cls = PluginRegistry.get_worker(name)
        config_dict = PluginRegistry.get_config(name)
        
        status = []
        if client_cls: status.append("Client [OK]") 
        else: status.append("Client [MISSING]") 
        
        if worker_cls: status.append("Worker [OK]") 
        else: status.append("Worker [MISSING]")
        
        if config_dict: status.append("Config [OK]") 
        else: status.append("Config [MISSING]")

        logger.info(f"      Status: {', '.join(status)}")
        
        if not (client_cls and worker_cls and config_dict):
            logger.error(f"      [X] Incomplete registration for {name}")
            all_passed = False
        else:
            # 打印配置键值概览
            keys = list(config_dict.keys())
            logger.info(f"      Config Keys: {keys}")

    # 3. 结果汇总
    logger.info("\n3. Verification Summary")
    if all_passed:
        logger.info("   [SUCCESS] All plugins are correctly decentralized and registered!")
        sys.exit(0)
    else:
        logger.error("   [FAILURE] Some plugins failed verification.")
        sys.exit(1)

if __name__ == "__main__":
    main()

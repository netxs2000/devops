"""DevOps Collector Worker

主要的 Worker 进程，负责：
1. 监听 RabbitMQ 任务队列
2. 解析任务消息
3. 将任务分发给对应的插件 Worker
"""
import time
import logging
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import Config
from .models.base_models import Base
from .mq import MessageQueue
from .core.registry import PluginRegistry

# 确保所有插件已注册
from .plugins import gitlab, sonarqube

logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger('Worker')

def _get_plugin_configs(source: str) -> dict:
    """根据数据源获取对应的配置参数。
    
    Args:
        source: 数据源名称 (gitlab, sonarqube, jenkins 等)
        
    Returns:
        包含 client 和 worker 配置的字典
    """
    configs = {
        'gitlab': {
            'client': {
                'url': Config.GITLAB_URL,
                'token': Config.GITLAB_PRIVATE_TOKEN,
                'rate_limit': Config.REQUESTS_PER_SECOND
            },
            'worker': {
                'enable_deep_analysis': Config.ENABLE_DEEP_ANALYSIS
            }
        },
        'sonarqube': {
            'client': {
                'url': Config.SONARQUBE_URL,
                'token': Config.SONARQUBE_TOKEN,
                'rate_limit': Config.REQUESTS_PER_SECOND
            },
            'worker': {
                'sync_issues': Config.SONARQUBE_SYNC_ISSUES
            }
        },
        'jenkins': {
            'client': {
                'url': Config.JENKINS_URL,
                'token': Config.JENKINS_TOKEN,
                'user': Config.JENKINS_USER
            },
            'worker': {
                'build_limit': Config.JENKINS_BUILD_SYNC_LIMIT
            }
        }
    }
    return configs.get(source, {'client': {}, 'worker': {}})

def process_task(ch, method, properties, body):
    """处理 MQ 消息的回调函数。"""
    task = {}
    session = None
    try:
        task = json.loads(body)
        source = task.get('source', 'gitlab')
        
        logger.info(f"Received task: {task} (source={source})")
        
        # 获取配置
        plugin_cfg = _get_plugin_configs(source)
        
        # 1. 自动实例化客户端
        client = PluginRegistry.get_client_instance(source, **plugin_cfg['client'])
        if not client:
            raise ValueError(f"No client registered or invalid config for source: {source}")
            
        # 2. 创建数据库会话
        engine = create_engine(Config.DB_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 3. 自动实例化 Worker
        worker = PluginRegistry.get_worker_instance(
            source, 
            session, 
            client, 
            **plugin_cfg['worker']
        )
        if not worker:
            raise ValueError(f"No worker registered for source: {source}")

        # 4. 执行任务
        worker.process_task(task)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Task for {source} processed successfully.")
        
    except Exception as e:
        logger.error(f"Error processing task: {e}")
        if session:
            session.rollback()
        ch.basic_ack(delivery_tag=method.delivery_tag)
    finally:
        if session:
            session.close()

def main():
    """Worker 主循环。"""
    # 确保表结构存在 (简单起见)
    engine = create_engine(Config.DB_URI)
    Base.metadata.create_all(engine)
    
    mq = MessageQueue()
    mq.consume(process_task)

if __name__ == "__main__":
    main()

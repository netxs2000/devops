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

def process_task(ch, method, properties, body):
    """处理 MQ 消息的回调函数。"""
    task = {}
    session = None
    try:
        task = json.loads(body)
        source = task.get('source', 'gitlab') # 默认为 gitlab (向后兼容)
        
        logger.info(f"Received task: {task} (source={source})")
        
        # 获取对应的 Worker 类
        worker_cls = PluginRegistry.get_worker(source)
        if not worker_cls:
            raise ValueError(f"No worker registered for source: {source}")
            
        # 获取对应的 Client 类
        client_cls = PluginRegistry.get_client(source)
        if not client_cls:
            raise ValueError(f"No client registered for source: {source}")
            
        # 实例化 Client
        client = None
        if source == 'gitlab':
            client = client_cls(
                url=Config.GITLAB_URL, 
                token=Config.GITLAB_PRIVATE_TOKEN,
                rate_limit=Config.REQUESTS_PER_SECOND
            )
        elif source == 'sonarqube':
            client = client_cls(
                url=Config.SONARQUBE_URL,
                token=Config.SONARQUBE_TOKEN,
                rate_limit=Config.REQUESTS_PER_SECOND
            )
        else:
            raise ValueError(f"Unknown source or missing config for: {source}")
            
        # 创建数据库会话
        engine = create_engine(Config.DB_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 实例化并执行 Worker
        worker = None
        if source == 'gitlab':
            worker = worker_cls(
                session, 
                client, 
                enable_deep_analysis=Config.ENABLE_DEEP_ANALYSIS
            )
        elif source == 'sonarqube':
            worker = worker_cls(
                session, 
                client, 
                sync_issues=Config.SONARQUBE_SYNC_ISSUES
            )
        else:
            # Fallback for generic workers
            worker = worker_cls(session, client)

        worker.process_task(task)
        
        # 确认消息处理完成
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Task processed successfully.")
        
    except Exception as e:
        logger.error(f"Error processing task: {e}")
        if session:
            session.rollback()
        # 这里可以选择拒绝消息(requeue=False)或重试(requeue=True)
        # 为防止死循环，暂时不重试
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

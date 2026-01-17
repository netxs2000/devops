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
from .core.plugin_loader import PluginLoader
# 触发插件自动发现
import devops_collector.plugins

logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger('Worker')


def process_task(ch, method, properties, body):
    """处理 MQ 消息的回调函数。"""
    task = {}
    session = None
    try:
        task = json.loads(body)
        source = task.get('source', 'unknown')
        logger.info(f'Received task: {task} (source={source})')
        
        # 1. 获取插件配置 (动态)
        plugin_cfg = PluginRegistry.get_config(source)
        if not plugin_cfg:
            # 如果未注册配置，尝试使用空配置（或者这里也可以选择报错）
            logger.warning(f'No config registered for source: {source}, using defaults.')
            plugin_cfg = {'client': {}, 'worker': {}}

        # 2. 获取并实例化客户端
        client_kwargs = plugin_cfg.get('client', {})
        client = PluginRegistry.get_client_instance(source, **client_kwargs)
        if not client:
            raise ValueError(f'No client registered for source: {source}')

        # 3. 准备数据库会话
        engine = create_engine(Config.DB_URI)
        Session = sessionmaker(bind=engine)
        session = Session()

        # 4. 获取并实例化 Worker
        worker_kwargs = plugin_cfg.get('worker', {})
        worker = PluginRegistry.get_worker_instance(source, session, client, **worker_kwargs)
        if not worker:
            raise ValueError(f'No worker registered for source: {source}')

        # 5. 执行任务
        worker.process_task(task)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f'Task for {source} processed successfully.')

    except Exception as e:
        logger.error(f'Error processing task: {e}', exc_info=True)
        if session:
            session.rollback()
        # 即使失败也确认消息，防止死循环 (或者根据需求放入死信队列)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    finally:
        if session:
            session.close()


def main():
    """Worker 主循环。"""
    # 显式加载所有插件模型，确保 Base.metadata 包含完整的表结构
    PluginLoader.load_models()
    
    engine = create_engine(Config.DB_URI)
    Base.metadata.create_all(engine)
    mq = MessageQueue()
    mq.consume_tasks(process_task)
if __name__ == '__main__':
    main()
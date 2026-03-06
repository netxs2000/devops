"""DevOps Collector Worker

主要的 Worker 进程，负责：
1. 监听 RabbitMQ 任务队列
2. 解析任务消息
3. 将任务分发给对应的插件 Worker
"""

import json
import logging
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 触发插件自动发现
from .config import Config
from .core.plugin_loader import PluginLoader
from .core.registry import PluginRegistry
from .models.base_models import Base
from .mq import MessageQueue


logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger("Worker")

# 模块级数据库连接池 (全局唯一，多任务共享)
_engine = create_engine(
    Config.DB_URI,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)
_SessionFactory = sessionmaker(bind=_engine)


def process_task(ch, method, properties, body):
    """处理 MQ 消息的回调函数。"""
    task = {}
    session = None
    
    # 获取 Correlation ID (优先从 properties 获取，兼容旧版本从 task 获取)
    correlation_id = properties.correlation_id
    try:
        task = json.loads(body)
        if not correlation_id:
            correlation_id = task.get("correlation_id", "unknown-cid")
    except Exception:
        correlation_id = correlation_id or "corrupt-payload"

    adapter = logging.LoggerAdapter(logger, {"correlation_id": correlation_id})
    
    start_time = time.perf_counter()
    try:
        source = task.get("source", "unknown")
        job_type = task.get("job_type", "unknown")
        adapter.info(f"Received task for {source} [CID: {correlation_id}]")

        # 1. 获取插件配置 (动态)
        plugin_cfg = PluginRegistry.get_config(source)
        if not plugin_cfg:
            adapter.warning(f"No config registered for source: {source}, using defaults.")
            plugin_cfg = {"client": {}, "worker": {}}

        # 2. 获取并实例化客户端
        client_kwargs = plugin_cfg.get("client", {})
        client = PluginRegistry.get_client_instance(source, **client_kwargs)
        if not client:
            raise ValueError(f"No client registered for source: {source}")

        # 3. 从连接池获取数据库会话
        session = _SessionFactory()

        # 4. 获取并实例化 Worker
        worker_kwargs = plugin_cfg.get("worker", {})
        worker = PluginRegistry.get_worker_instance(source, session, client, correlation_id=correlation_id, **worker_kwargs)
        if not worker:
            raise ValueError(f"No worker registered for source: {source}")

        # 5. 执行任务
        worker.process_task(task)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        adapter.info(
            f"Task for {source} processed successfully.",
            extra={
                "metric_type": "sync_task",
                "status": "success",
                "source": source,
                "job_type": job_type,
                "duration_ms": duration_ms
            }
        )

    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        adapter.error(
            f"Error processing task: {e}",
            exc_info=True,
            extra={
                "metric_type": "sync_task",
                "status": "failure",
                "error_type": type(e).__name__,
                "source": source,
                "duration_ms": duration_ms
            }
        )
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

    Base.metadata.create_all(_engine)
    mq = MessageQueue()
    mq.consume_tasks(process_task)


if __name__ == "__main__":
    main()

"""RabbitMQ 消息队列封装模块

提供任务发布和消费的统一接口，支持持久化消息。

队列名称: gitlab_tasks
"""

import json
import logging
import uuid

import pika

from .config import Config


logger = logging.getLogger(__name__)


class MessageQueue:
    """RabbitMQ 消息队列客户端。

    提供任务发布和消费方法，自动管理连接状态。

    Attributes:
        url: RabbitMQ 连接 URL
        channel: AMQP 通道

    Example:
        mq = MessageQueue()
        mq.publish_task({'project_id': 123, 'job_type': 'full'})
    """

    def __init__(self):
        """初始化 MQ 客户端，增加心跳以维持长任务连接。"""
        self.url = Config.RABBITMQ_URL
        # 增加 heartbeat 以防止长任务处理期间连接被 RabbitMQ 断开 (默认 60s)
        if "?" in self.url:
            self.url += "&heartbeat=600"
        else:
            self.url += "?heartbeat=600"

        self.params = pika.URLParameters(self.url)
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        try:
            self.connection = pika.BlockingConnection(self.params)
            self.channel = self.connection.channel()
            for q in ["gitlab_tasks", "zentao_tasks", "sonarqube_tasks"]:
                self.channel.queue_declare(queue=q, durable=True)
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise e

    def publish_task(self, task: dict) -> None:
        """发布同步任务到队列。

        Args:
            task: 任务字典，包含 project_id 和 job_type
        """
        if not self.channel or self.connection.is_closed:
            self.connect()
        source = task.get("source", "gitlab")
        queue_name = f"{source}_tasks"
        
        # 注入 Correlation ID
        correlation_id = task.get("correlation_id")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            task["correlation_id"] = correlation_id

        self.channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(task),
            properties=pika.BasicProperties(
                delivery_mode=2,
                correlation_id=correlation_id
            ),
        )
        logger.info(f"Published task to {queue_name} [CorrelationID: {correlation_id}]: {task}")

    def consume_tasks(self, callback) -> None:
        """开始消费任务队列 (阻塞式)。

        Args:
            callback: 消息处理回调函数，签名为 (ch, method, properties, body)
        """
        if not self.channel or self.connection.is_closed:
            self.connect()
        self.channel.basic_qos(prefetch_count=1)
        for q in ["gitlab_tasks", "zentao_tasks", "sonarqube_tasks"]:
            self.channel.basic_consume(queue=q, on_message_callback=callback)
        logger.info("Waiting for tasks on all queues...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            raise e

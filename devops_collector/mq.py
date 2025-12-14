"""RabbitMQ 消息队列封装模块

提供任务发布和消费的统一接口，支持持久化消息。

队列名称: gitlab_tasks
"""
import pika
import json
import logging
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
        self.url = Config.RABBITMQ_URL
        self.params = pika.URLParameters(self.url)
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        try:
            self.connection = pika.BlockingConnection(self.params)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue='gitlab_tasks', durable=True)
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
        
        self.channel.basic_publish(
            exchange='',
            routing_key='gitlab_tasks',
            body=json.dumps(task),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))
        logger.info(f"Published task: {task}")

    def consume_tasks(self, callback) -> None:
        """开始消费任务队列 (阻塞式)。
        
        Args:
            callback: 消息处理回调函数，签名为 (ch, method, properties, body)
        """
        if not self.channel or self.connection.is_closed:
            self.connect()
            
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue='gitlab_tasks', on_message_callback=callback)
        
        logger.info("Waiting for tasks...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            raise e

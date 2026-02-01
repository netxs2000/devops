import sys
import os
import pika
from typing import Optional

# 将项目根目录添加到 python 路径
sys.path.insert(0, os.getcwd())

from devops_collector.config import settings

def diagnose_mq():
    """诊断 RabbitMQ 连接和队列状态。"""
    print("=" * 60)
    print("RabbitMQ 专项诊断")
    print("=" * 60)

    host = settings.rabbitmq.host
    user = settings.rabbitmq.user
    password = settings.rabbitmq.password
    port = settings.rabbitmq.port

    print(f"尝试连接到 RabbitMQ: {host}:{port} (User: {user})")

    try:
        credentials = pika.PlainCredentials(user, password)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=host, port=port, credentials=credentials, timeout=5)
        )
        channel = connection.channel()
        
        print("✓ 连接成功")

        # 检查一些核心队列 (如果已知名称)
        # 这里仅列出连接成功
        
        connection.close()
        print("✓ 连接关闭正常")
        return True
    except Exception as e:
        print(f"✗ RabbitMQ 连接失败: {e}")
        return False

if __name__ == "__main__":
    success = diagnose_mq()
    sys.exit(0 if success else 1)

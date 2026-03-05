#!/bin/bash
set -e

# 等待数据库 就绪
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z $DB_HOST 5432; do
  sleep 1
done
echo "✅ PostgreSQL is up!"

# 等待 RabbitMQ 就绪
echo "⏳ Waiting for RabbitMQ..."
while ! nc -z $RABBIT_HOST 5672; do
  sleep 1
done
echo "✅ RabbitMQ is up!"

# 执行数据库自动初始化/迁移 (建议在大规模环境下手动执行)
# echo "🚀 Running auto-initialization..."
# python scripts/init_discovery.py || echo "⚠️ Discovery init failed or already done"

# 执行 SQL 视图部署 (如果有相关脚本)
# python scripts/deploy_views.py

# 继续执行后续命令 (CMD)
exec "$@"

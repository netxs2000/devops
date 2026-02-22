"""数据库重置工具 (PostgreSQL 增强版).

作用：强制清空公共 Schema 下的所有表，解决 SQLAlchemy drop_all 在循环外键下的限制。
"""
import logging
import os
import sys

from sqlalchemy import create_engine, text


sys.path.append(os.getcwd())
from devops_collector.config import settings
from devops_collector.models.base_models import Base


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DBReset')

def reset_database():
    engine = create_engine(settings.database.uri)

    logger.warning("！！！警告：正在重置数据库，全量数据将被清空！！！")

    try:
        with engine.connect() as conn:
            # 1. 强制断开其他连接
            db_name = settings.database.uri.split('/')[-1]
            terminate_sql = f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
              AND pid <> pg_backend_pid();
            """
            try:
                conn.execute(text(terminate_sql))
                conn.commit()
            except Exception:
                pass

            # 2. 清理 Schema (Postgres 专用最强清理法)
            # 这种方式比 drop_all 更彻底，且能处理任何复杂的循环依赖
            logger.info("清理 public schema...")
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            conn.commit()
            logger.info("public schema 已重置。")

        # 3. 重新创建所有表
        Base.metadata.create_all(engine)
        logger.info("数据库 Schema 已根据当前模型重建。")

    except Exception as e:
        logger.error(f"数据库重置失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_database()

"""数据库 Schema 自动增量同步工具。

通过对比 SQLAlchemy 模型与数据库实际表结构，自动执行 ALTER TABLE 补全缺失列。
"""
import logging
from sqlalchemy import create_engine, inspect, text
from devops_collector.models import Base
from devops_collector.config import settings

logger = logging.getLogger(__name__)

def auto_sync_schema():
    """自动化同步数据库结构 (仅支持新增列)。"""
    engine = create_engine(settings.database.uri)
    inspector = inspect(engine)
    
    # 1. 确保所有表都至少存在 (create_all)
    Base.metadata.create_all(engine)
    
    with engine.connect() as conn:
        logger.info("Scanning for schema differences...")
        
        for table_name, table in Base.metadata.tables.items():
            # 获取数据库中该表已有的列名
            try:
                existing_columns = [c['name'] for c in inspector.get_columns(table_name)]
            except Exception:
                # 表可能刚创建或不存在
                continue
            
            # 遍历模型中定义的列
            for column in table.columns:
                if column.name not in existing_columns:
                    logger.info(f"Detect missing column: {table_name}.{column.name}")
                    
                    # 构建增量添加列的 SQL (Postgres 语法)
                    # 虽然 SQLAlchemy 支持 type.compile，但基础类型直接拼凑更稳健
                    col_type = column.type.compile(engine.dialect)
                    nullable = "NULL" if column.nullable else "NOT NULL"
                    default = f"DEFAULT {column.default.arg}" if column.default else ""
                    
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"
                    
                    try:
                        conn.execute(text(sql))
                        conn.commit()
                        logger.info(f"Successfully added column {column.name} to {table_name}")
                    except Exception as e:
                        logger.error(f"Failed to sync column {column.name}: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    auto_sync_schema()

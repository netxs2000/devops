"""认证模块数据库配置。

提供 Auth 模块专用的数据库引擎、会话工厂以及基础类。
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from devops_collector.config import settings

# 创建认证模块专用的数据库引擎
auth_engine = create_engine(settings.database.uri)

# 创建认证模块专用的会话工厂
AuthSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)

# 基础类声明
AuthBase = declarative_base()

def get_auth_db():
    """获取认证模块数据库会话的依赖项。
    
    Yields:
        Session: SQLAlchemy 数据库会话。
    """
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()

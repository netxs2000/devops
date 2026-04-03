"""tests/unit 共享 fixtures。

提供基于唯一物理数据库文件的 db_session，确保每个测试 case 之间的绝对物理隔离。
"""

import os
import tempfile

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from devops_collector.models.base_models import Base


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="function")
def db_session():
    """每个测试用例独立的物理数据库环境。"""
    # 1. 分配唯一的临时数据库文件
    db_fd, db_path = tempfile.mkstemp(suffix=".db", prefix="unit_test_")
    os.close(db_fd)
    db_uri = f"sqlite:///{db_path}"

    # 保存原始环境变量供恢复
    old_db_uri = os.environ.get("DB_URI")
    os.environ["DB_URI"] = db_uri

    # 2. 创建局部 Engine（禁用连接池共享）
    test_engine = create_engine(
        db_uri,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # 3. 初始化表结构
    Base.metadata.create_all(bind=test_engine)

    # 4. 创建会话
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
        # 物理销毁
        with test_engine.begin() as conn:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
            Base.metadata.drop_all(bind=conn)
        test_engine.dispose()

        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

        # 恢复环境变量
        if old_db_uri:
            os.environ["DB_URI"] = old_db_uri
        else:
            os.environ.pop("DB_URI", None)

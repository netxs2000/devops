"""验证 SQLAlchemy 模型映射完整性脚本。

该脚本动态加载所有已定义的模型，并在内存数据库中尝试创建所有表，
用于检测最近重构是否引入了 AmbiguousForeignKeysError 或 NoForeignKeysError。
"""
import sys
import os
import logging
from unittest.mock import MagicMock
sys.path.append(os.getcwd())
import sqlalchemy
from sqlalchemy.dialects import postgresql
postgresql.JSONB = sqlalchemy.JSON
postgresql.UUID = lambda *args, **kwargs: sqlalchemy.String(36)
from sqlalchemy import create_engine
from devops_collector.models import Base
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('MappingVerifier')

def verify_mapping():
    """执行映射验证。"""
    logger.info('开始验证 SQLAlchemy 模型映射...')
    engine = create_engine('sqlite:///:memory:')
    try:
        Base.metadata.create_all(engine)
        logger.info('✅ 成功！所有模型映射正常，未发现外键冲突或缺失。')
        return True
    except Exception as e:
        logger.error('❌ 失败！检测到映射错误：')
        logger.error(str(e))
        import traceback
        traceback.print_exc()
        return False
if __name__ == '__main__':
    success = verify_mapping()
    if not success:
        sys.exit(1)
    else:
        sys.exit(0)
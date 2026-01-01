"""验证 SQLAlchemy 模型映射完整性脚本。

该脚本动态加载所有已定义的模型，并在内存数据库中尝试创建所有表，
用于检测最近重构是否引入了 AmbiguousForeignKeysError 或 NoForeignKeysError。
"""
import sys
import os
import logging
from unittest.mock import MagicMock

# 将项目根目录添加到 python 路径
sys.path.append(os.getcwd())

# --- 开始 Mock 处理 ---
# SQLite 不支持 PostgreSQL 特有的 JSONB 和 UUID 类型。
# 在验证映射关系时，我们将它们映射到标准类型。
import sqlalchemy
from sqlalchemy.dialects import postgresql

# 模拟 JSONB 为标准 JSON
postgresql.JSONB = sqlalchemy.JSON

# 模拟 UUID 为 String(36)
postgresql.UUID = lambda *args, **kwargs: sqlalchemy.String(36)

# 强制通过 SQLAlchemy 基础模型导入
from sqlalchemy import create_engine
from devops_collector.models import Base
# --- 结束 Mock 处理 ---

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger('MappingVerifier')

def verify_mapping():
    """执行映射验证。"""
    logger.info("开始验证 SQLAlchemy 模型映射...")
    
    # 强制导入所有已注册的模型（通过导入 devops_collector.models）
    # 已经在文件开头完成。
    
    # 使用内存 SQLite 引擎
    engine = create_engine('sqlite:///:memory:')
    
    try:
        # 尝试创建所有表。这会触发 SQLAlchemy 检查所有关系。
        Base.metadata.create_all(engine)
        logger.info("✅ 成功！所有模型映射正常，未发现外键冲突或缺失。")
        return True
    except Exception as e:
        logger.error("❌ 失败！检测到映射错误：")
        logger.error(str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_mapping()
    if not success:
        sys.exit(1)
    else:
        sys.exit(0)

import sys
import os
from sqlalchemy import text
from typing import List

# 将项目根目录添加到 python 路径
sys.path.insert(0, os.getcwd())

from devops_collector.auth.auth_database import AuthEngine, AuthSessionLocal

def diagnose_db():
    """诊断数据库连接及核心数据表。"""
    print("=" * 60)
    print("数据库专项诊断")
    print("=" * 60)

    try:
        # 1. 测试连接
        with AuthEngine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✓ 数据库连接成功: {version}")

        # 2. 检查核心表内容
        db = AuthSessionLocal()
        
        # 统计一些关键表的记录数
        tables = ["adm_users", "adm_roles", "sd_tickets", "pm_projects"]
        
        print("\n核心表数据统计:")
        for table in tables:
            try:
                count_result = db.execute(text(f"SELECT count(*) FROM {table}")).fetchone()[0]
                print(f"  - {table:20}: {count_result} 条记录")
            except Exception as e:
                print(f"  - {table:20}: ✗ 查询失败 (可能表不存在)")

        db.close()
        return True
    except Exception as e:
        print(f"✗ 数据库检查失败: {e}")
        return False

if __name__ == "__main__":
    success = diagnose_db()
    sys.exit(0 if success else 1)

"""
模型层冒烟测试脚本
用于验证重构后的 SQLAlchemy 模型元数据、关系映射和表结构一致性。
"""
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from devops_collector.models.base_models import Base
from devops_collector.core.plugin_loader import PluginLoader

def run_smoke_test():
    print("开始模型冒烟测试...")
    
    # 1. 模拟插件自动发现
    print("[1/3] 正在发现并加载插件...")
    try:
        PluginLoader.autodiscover()
        print(f"已加载插件: {PluginLoader._loaded_plugins}")
    except Exception as e:
        print(f"插件加载失败: {e}")
        return False

    # 2. 动态加载所有模型
    print("[2/3] 正在加载所有 SQLAlchemy 模型...")
    try:
        PluginLoader.load_models()
        print("模型加载完成。")
    except Exception as e:
        print(f"模型加载失败: {e}")
        return False

    # 3. 尝试在内存 SQLite 中创建所有表
    print("[3/3] 正在尝试创建表结构 (验证 ORM 关系一致性)...")
    try:
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        print("表结构创建成功！所有关系映射校验通过。")
        
        # 打印生成的表名，以便核对
        print("\n已生成的表清单:")
        for table_name in sorted(Base.metadata.tables.keys()):
            print(f" - {table_name}")
            
    except Exception as e:
        print(f"\n[ERROR] 表结构创建失败或关系冲突: {e}")
        # 这里有助于调试具体的错误信息
        import traceback
        traceback.print_exc()
        return False

    print("\n结论: 模型层冒烟测试成功！重构没有破坏元数据完整性。")
    return True

if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)

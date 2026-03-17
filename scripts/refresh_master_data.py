"""定向刷新主数据 (Directed Master Data Refresh).

作用：
1. 解除业务数据与旧主数据的关联 (Set FKs to NULL)。
2. 清空产品/项目/组织等主数据表。
3. 执行初始化脚本重新注入新主数据。

使用示例:
    python scripts/refresh_master_data.py --scope all
    python scripts/refresh_master_data.py --scope products
"""

import argparse
import logging
import sys
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def run_script(script_path):
    """执行子脚本。"""
    logger.info(f"正在执行初始化脚本: {script_path}")
    try:
        # 使用当前 python 解释器执行
        subprocess.run([sys.executable, str(script_path)], check=True)
        logger.info(f"脚本 {script_path.name} 执行成功。")
    except subprocess.CalledProcessError as e:
        logger.error(f"脚本 {script_path.name} 执行失败 (退出码: {e.returncode})")
        raise

def refresh_master_data(scope):
    """定向重置逻辑。"""
    engine = create_engine(settings.database.uri)
    root_dir = Path(__file__).parent.parent
    
    logger.info(f"===> 开始定向重置主数据 [范围: {scope}] <===")

    with engine.begin() as conn:
        # 1. 解除外部系统映射 (Nullify Foreign Keys)
        if scope in ["all", "products", "projects"]:
            logger.info("第一阶段：解除外部系统与主数据的关联...")
            
            # TODO: 动态探测插件表是否存在，目前先硬编码核心表
            nullify_queries = [
                "UPDATE zentao_products SET mdm_product_id = NULL",
                "UPDATE zentao_executions SET mdm_project_id = NULL",
                "UPDATE gitlab_projects SET mdm_project_id = NULL",
                "UPDATE mdm_entity_topology SET project_id = NULL",
                "UPDATE rpt_commit_metrics SET project_id = NULL",
                "UPDATE mdm_compliance_issues SET entity_id = NULL WHERE issue_type IN ('PROJECT', 'SERVICE')"
            ]
            
            for query in nullify_queries:
                try:
                    conn.execute(text(query))
                    logger.debug(f"执行成功: {query}")
                except Exception as e:
                    logger.warning(f"跳过执行 (可能表或列不存在): {query} - 错误: {e}")

        # 2. 清理表数据
        logger.info("第二阶段：清理主数据表...")
        
        if scope in ["all", "projects"]:
            logger.info("清理项目关联与主表...")
            conn.execute(text("DELETE FROM mdm_rel_project_product"))
            conn.execute(text("DELETE FROM mdm_projects"))
            
        if scope in ["all", "products"]:
            logger.info("清理产品主表 (处理自引用约束)...")
            conn.execute(text("UPDATE mdm_products SET parent_product_id = NULL"))
            conn.execute(text("DELETE FROM mdm_products"))

        if scope == "all":
            logger.info("清理组织架构 (处理自引用约束)...")
            conn.execute(text("UPDATE mdm_organizations SET parent_id = NULL"))
            conn.execute(text("DELETE FROM mdm_organizations WHERE org_code != 'ORG-HQ'"))

    # 3. 重新注入数据
    logger.info("第三阶段：重新注入主数据...")
    
    scripts_to_run = []
    if scope == "all":
        scripts_to_run.append(root_dir / "scripts" / "init_organizations.py")
    
    if scope in ["all", "products", "projects"]:
        scripts_to_run.append(root_dir / "scripts" / "init_products_projects.py")
        
    for script in scripts_to_run:
        if script.exists():
            run_script(script)
        else:
            logger.warning(f"找不到初始化脚本: {script}")

    logger.info("===> ✅ 定向刷新任务圆满完成！<===")

def main():
    parser = argparse.ArgumentParser(description="DevOps 平台主数据定向刷新工具")
    parser.add_argument(
        "--scope", 
        choices=["all", "products", "projects"], 
        default="all",
        help="重置范围: all (组织+产品+项目), products (产品+项目), projects (仅项目)"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="强制执行，不提示确认"
    )
    
    args = parser.parse_args()

    if not args.force:
        confirm = input(f"此操作将清除数据库中的 {args.scope} 主数据并重新从 CSV 注入，但会保留业务割取历史。确认继续？(y/n): ")
        if confirm.lower() != 'y':
            print("操作已取消。")
            return

    try:
        refresh_master_data(args.scope)
    except Exception as e:
        logger.error(f"任务执行中断: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

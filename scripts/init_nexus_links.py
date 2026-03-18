import csv
import logging
import os
import re

from devops_collector.auth.auth_database import AuthSessionLocal
from devops_collector.models.base_models import Product
from devops_collector.plugins.nexus.models import NexusComponent


# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

NEXUS_MAP_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "nexus_component_map.csv")


def init_nexus_links():
    """根据 CSV 映射文件初始化 Nexus 组件与 MDM 产品的关联。"""
    session = AuthSessionLocal()
    if not os.path.exists(NEXUS_MAP_CSV):
        logger.warning(f"找不到映射文件: {NEXUS_MAP_CSV}")
        return

    try:
        logger.info("开始同步 Nexus 组件关联 (高性能模式)...")

        # 1. 预加载所有有效产品到内存 (映射 Code -> ID)
        all_products = session.query(Product.id, Product.product_code).filter(Product.is_current).all()
        # 建立双向映射或优先 Code 映射，确保 CSV 中的业务代号能找到物理 ID
        product_code_map = {p.product_code: p.id for p in all_products}
        product_id_set = {p.id for p in all_products}
        logger.info(f"已加载 {len(product_code_map)} 个有效产品。")

        # 2. 预加载并编译所有映射规则
        rules = []
        with open(NEXUS_MAP_CSV, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                group_pat = row.get("group", "").strip()
                name_pat = row.get("name", "").strip()
                mdm_prod_id_raw = row.get("mdm_product_id", "").strip()
                match_type = row.get("match_type", "exact").strip().lower()

                if (not group_pat and not name_pat) or not mdm_prod_id_raw:
                    continue

                # 识别 mdm_prod_id_raw 是业务 Code 还是物理 ID
                actual_pid = None
                if mdm_prod_id_raw in product_code_map:
                    actual_pid = product_code_map[mdm_prod_id_raw]
                elif mdm_prod_id_raw.isdigit() and int(mdm_prod_id_raw) in product_id_set:
                    actual_pid = int(mdm_prod_id_raw)

                if actual_pid is None:
                    logger.warning(f"MDM 产品标识 '{mdm_prod_id_raw}' 不存在或非当前版本，跳过该规则.")
                    continue

                rule = {
                    "group": group_pat,
                    "name": name_pat,
                    "pid": actual_pid,
                    "type": match_type,
                    "group_re": re.compile(group_pat) if match_type == "regex" and group_pat else None,
                    "name_re": re.compile(name_pat) if match_type == "regex" and name_pat else None,
                }
                rules.append(rule)

        logger.info(f"已加载 {len(rules)} 条映射规则。")

        # 3. 遍历所有组件一次进行匹配 (O(Rules * Components))
        # 使用 yield_per 降低大表内存压力
        all_components = session.query(NexusComponent).yield_per(1000)
        match_stats = {}  # pid -> count
        updated_count = 0

        for comp in all_components:
            for rule in rules:
                is_match = True

                if rule["type"] == "regex":
                    if rule["group"] and not rule["group_re"].search(comp.group or ""):
                        is_match = False
                    if rule["name"] and not rule["name_re"].search(comp.name or ""):
                        is_match = False
                else:  # exact
                    if rule["group"] and comp.group != rule["group"]:
                        is_match = False
                    if rule["name"] and comp.name != rule["name"]:
                        is_match = False

                if is_match:
                    if comp.product_id != rule["pid"]:
                        comp.product_id = rule["pid"]
                        updated_count += 1
                        match_stats[rule["pid"]] = match_stats.get(rule["pid"], 0) + 1
                    break  # 匹配到第一条规则即停止

        if updated_count > 0:
            for pid, count in match_stats.items():
                logger.info(f"产品 {pid} 关联了 {count} 个组件。")
            logger.info(f"本次共更新 {updated_count} 个组件的关联关系。")
        else:
            logger.info("未发现需要更新的关联关系。")

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"同步失败: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    init_nexus_links()

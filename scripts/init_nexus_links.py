import csv
import os
import logging
import re
from sqlalchemy.orm import Session
from devops_collector.models.database import SessionLocal
from devops_collector.plugins.nexus.models import NexusComponent
from devops_collector.models.base_models import Product

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

NEXUS_MAP_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs', 'nexus_component_map.csv')

def init_nexus_links():
    """根据 CSV 映射文件初始化 Nexus 组件与 MDM 产品的关联。"""
    if not os.path.exists(NEXUS_MAP_CSV):
        logger.warning(f"找不到映射文件: {NEXUS_MAP_CSV}")
        return

    try:
        logger.info("开始同步 Nexus 组件关联 (高性能模式)...")
        
        # 1. 预加载所有有效产品到内存
        all_products = session.query(Product.product_id).filter(Product.is_current == True).all()
        valid_product_ids = {p.product_id for p in all_products}
        logger.info(f"已加载 {len(valid_product_ids)} 个有效产品。")

        # 2. 预加载并编译所有映射规则
        rules = []
        with open(NEXUS_MAP_CSV, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                group_pat = row.get('group', '').strip()
                name_pat = row.get('name', '').strip()
                mdm_prod_id = row.get('mdm_product_id', '').strip()
                match_type = row.get('match_type', 'exact').strip().lower()

                if (not group_pat and not name_pat) or not mdm_prod_id:
                    continue

                if mdm_prod_id not in valid_product_ids:
                    logger.warning(f"MDM 产品 {mdm_prod_id} 不存在，跳过该规则.")
                    continue

                rule = {
                    'group': group_pat,
                    'name': name_pat,
                    'pid': mdm_prod_id,
                    'type': match_type,
                    'group_re': re.compile(group_pat) if match_type == 'regex' and group_pat else None,
                    'name_re': re.compile(name_pat) if match_type == 'regex' and name_pat else None
                }
                rules.append(rule)
        
        logger.info(f"已加载 {len(rules)} 条映射规则。")

        # 3. 遍历所有组件一次进行匹配 (O(Rules * Components))
        # 使用 yield_per 降低大表内存压力
        all_components = session.query(NexusComponent).yield_per(1000)
        match_stats = {} # pid -> count
        updated_count = 0

        for comp in all_components:
            for rule in rules:
                is_match = True
                
                if rule['type'] == 'regex':
                    if rule['group'] and not rule['group_re'].search(comp.group or ''):
                        is_match = False
                    if rule['name'] and not rule['name_re'].search(comp.name or ''):
                        is_match = False
                else: # exact
                    if rule['group'] and comp.group != rule['group']:
                        is_match = False
                    if rule['name'] and comp.name != rule['name']:
                        is_match = False
                        
                if is_match:
                    if comp.product_id != rule['pid']:
                        comp.product_id = rule['pid']
                        updated_count += 1
                        match_stats[rule['pid']] = match_stats.get(rule['pid'], 0) + 1
                    break # 匹配到第一条规则即停止

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

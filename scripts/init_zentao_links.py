"""初始化禅道 (ZenTao) 项目与产品关联映射。

本脚本读取 docs/zentao_product_map.csv 和 docs/zentao_project_map.csv，
建立禅道实体与 DevOps 平台 MDM 主数据（Product/Project）的关联关系。

执行方式:
    python scripts/init_zentao_links.py
"""

import csv
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from devops_collector.config import settings
from devops_collector.models import EntityTopology, Product, ProjectMaster, SystemRegistry
from devops_collector.plugins.zentao.models import ZenTaoExecution, ZenTaoProduct


# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('InitZenTaoLinks')

PRODUCT_MAP_CSV = 'docs/zentao_product_map.csv'
PROJECT_MAP_CSV = 'docs/zentao_project_map.csv'

def ensure_system_registry(session: Session):
    """确保禅道系统在注册表中。"""
    system = session.query(SystemRegistry).filter_by(system_code='zentao').first()
    if not system:
        system = SystemRegistry(
            system_code='zentao',
            system_name='ZenTao ALM',
            system_type='TICKET',
            is_active=True
        )
        session.add(system)
        session.flush()
    return system

def init_product_links(session: Session):
    """同步产品关联。"""
    if not os.path.exists(PRODUCT_MAP_CSV):
        logger.warning(f"找不到产品映射文件: {PRODUCT_MAP_CSV}")
        return

    logger.info("开始同步禅道产品关联...")
    with open(PRODUCT_MAP_CSV, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            zt_pid = row.get('zentao_product_id', '').strip()
            mdm_pid = row.get('mdm_product_id', '').strip()

            if not zt_pid or not mdm_pid: continue

            # 1. 验证 MDM 产品是否存在
            mdm_product = session.query(Product).filter_by(product_id=mdm_pid).first()
            if not mdm_product:
                logger.warning(f"MDM 产品 {mdm_pid} 不存在，跳过。")
                continue

            # 2. 更新/创建 ZenTaoProduct 记录
            zt_product = session.query(ZenTaoProduct).filter_by(id=int(zt_pid)).first()
            if not zt_product:
                zt_product = ZenTaoProduct(id=int(zt_pid), name=f"ZenTao Product {zt_pid}")
                session.add(zt_product)

            zt_product.mdm_product_id = mdm_pid

            # 3. 更新 EntityTopology (用于 DORA/反向查询)
            topology = session.query(EntityTopology).filter_by(
                system_code='zentao',
                external_resource_id=zt_pid,
                element_type='issue-tracker-product'
            ).first()

            if not topology:
                topology = EntityTopology(
                    system_code='zentao',
                    external_resource_id=zt_pid,
                    resource_name=mdm_product.product_name,
                    element_type='issue-tracker-product',
                    is_active=True
                )
                session.add(topology)

            logger.info(f"建立关联: ZenTao Product {zt_pid} -> MDM Product {mdm_pid}")

def init_project_links(session: Session):
    """同步项目关联，并处理 20.0 版本的父子层级继承逻辑。"""
    if not os.path.exists(PROJECT_MAP_CSV):
        logger.warning(f"找不到项目映射文件: {PROJECT_MAP_CSV}")
        return

    logger.info("开始同步禅道项目/执行关联...")
    mappings = []
    with open(PROJECT_MAP_CSV, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            zt_eid = row.get('zentao_execution_id', '').strip()
            mdm_proj_id = row.get('mdm_project_id', '').strip()
            if zt_eid and mdm_proj_id:
                mappings.append((int(zt_eid), mdm_proj_id))

    for zt_id, mdm_id in mappings:
        # 1. 验证 MDM 项目是否存在
        mdm_project = session.query(ProjectMaster).filter_by(project_id=mdm_id).first()
        if not mdm_project:
            logger.warning(f"MDM 项目 {mdm_id} 不存在，跳过。")
            continue

        # 2. 查找并更新目标节点
        target_node = session.query(ZenTaoExecution).filter_by(id=zt_id).first()
        if target_node:
            target_node.mdm_project_id = mdm_id
            logger.info(f"直接关联: ZenTao Node {zt_id} ({target_node.type}) -> MDM Project {mdm_id}")

            # 3. 继承逻辑 (Inheritance): 利用 path 字段查找所有子孙节点
            # 禅道 path 格式通常为 ",1,5,10,"，如果我们要找 5 的子孙，匹配 "%,5,%"
            search_pattern = f"%,{zt_id},%"
            children = session.query(ZenTaoExecution).filter(
                ZenTaoExecution.path.like(search_pattern),
                ZenTaoExecution.id != zt_id
            ).all()

            for child in children:
                # 只有当子节点没有被 CSV 明确指定其他项目时，才进行继承
                if not any(m[0] == child.id for m in mappings):
                    child.mdm_project_id = mdm_id
                    logger.info(f"  └─ 自动继承: ZenTao Child {child.id} ({child.type}) -> MDM Project {mdm_id}")
        else:
            logger.info(f"ZenTao 节点 {zt_id} 尚未同步到本地表，仅建立拓扑映射。")

        # 4. 更新 EntityTopology (作为所有查询的根源)
        topology = session.query(EntityTopology).filter_by(
            project_id=mdm_id,
            system_code='zentao',
            external_resource_id=str(zt_id),
            element_type='issue-tracker'
        ).first()

        if not topology:
            topology = EntityTopology(
                project_id=mdm_id,
                system_code='zentao',
                external_resource_id=str(zt_id),
                resource_name=mdm_project.project_name,
                element_type='issue-tracker',
                is_active=True
            )
            session.add(topology)

def main():
    engine = create_engine(settings.database.uri)
    ensure_system_registry(Session(engine))

    with Session(engine) as session:
        try:
            init_product_links(session)
            init_project_links(session)
            session.commit()
            logger.info("禅道关联初始化完成！")
        except Exception as e:
            session.rollback()
            logger.error(f"同步失败: {e}")
            raise

if __name__ == '__main__':
    main()

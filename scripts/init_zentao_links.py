"""Initialize ZenTao project and product mappings.

This script reads docs/zentao_product_map.csv and docs/zentao_project_map.csv,
establishing links between ZenTao entities and MDM Master Data (Product/Project).

Execution:
    python scripts/init_zentao_links.py
"""

import csv
import logging
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from devops_collector.config import settings
from devops_collector.models import EntityTopology, Product, ProjectMaster, SystemRegistry
from devops_collector.plugins.zentao.models import ZenTaoExecution, ZenTaoProduct


# Logging config
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("InitZenTaoLinks")

PRODUCT_MAP_CSV = "docs/zentao_product_map.csv"
PROJECT_MAP_CSV = "docs/zentao_project_map.csv"


def ensure_system_registry(session: Session):
    """Ensure ZenTao is registered."""
    system = session.query(SystemRegistry).filter_by(system_code="zentao-prod").first()
    if not system:
        system = SystemRegistry(system_code="zentao-prod", system_name="ZenTao ALM", system_type="PROJECT", is_active=True, env_tag="PROD")
        session.add(system)
        session.flush()
    return system


def init_product_links(session: Session):
    """Sync product associations."""
    if not os.path.exists(PRODUCT_MAP_CSV):
        logger.warning(f"Could not find {PRODUCT_MAP_CSV}")
        return

    logger.info("Syncing ZenTao product links...")
    with open(PRODUCT_MAP_CSV, encoding="utf-8-sig") as f:
        lines = [line for line in f if not line.strip().startswith("#")]
        reader = csv.DictReader(lines)
        for row in reader:
            try:
                zt_ref = row.get("zentao_product_id", "").strip()
                zt_name = row.get("zentao_product_name", "").strip()
                mdm_ref = row.get("mdm_product_id", "").strip()
                mdm_name = row.get("mdm_product_name", "").strip()

                if not mdm_ref and not mdm_name:
                    continue

                # Find MDM Product
                mdm_product = (
                    session.query(Product)
                    .filter(
                        (Product.product_id == mdm_ref)
                        | (Product.product_id == f"PRD-{mdm_ref}")
                        | (Product.product_name == mdm_name)
                        | (Product.product_name == mdm_ref)
                    )
                    .first()
                )

                if not mdm_product:
                    logger.warning(f"Skip: MDM Product not found (Ref={mdm_ref}, Name={mdm_name})")
                    continue

                # Find ZenTao Product
                zt_product = None
                if zt_ref.isdigit():
                    zt_product = session.query(ZenTaoProduct).filter_by(id=int(zt_ref)).first()
                if not zt_product:
                    zt_product = session.query(ZenTaoProduct).filter((ZenTaoProduct.code == zt_ref) | (ZenTaoProduct.name == zt_name)).first()

                if zt_product:
                    zt_product.mdm_product_id = mdm_product.product_id

                    topology = (
                        session.query(EntityTopology)
                        .filter_by(system_code="zentao-prod", external_resource_id=str(zt_product.id), element_type="issue-tracker-product")
                        .first()
                    )
                    if not topology:
                        topology = EntityTopology(
                            system_code="zentao-prod",
                            external_resource_id=str(zt_product.id),
                            resource_name=zt_product.name,
                            element_type="issue-tracker-product",
                            is_active=True,
                            sync_version=1,
                        )
                        session.add(topology)
                    topology.project_id = None
                    session.flush()
                    if zt_product.id % 10 == 0:
                        session.commit()
                    logger.info(f"Linked Product: ZenTao '{zt_product.name}' -> MDM '{mdm_product.product_name}'")
                else:
                    logger.warning(f"Original ZenTao record not found: Ref={zt_ref}, Name={zt_name}")
            except Exception as e:
                session.rollback()
                logger.error(f"Row error (Product: {row}): {e}")


def init_project_links(session: Session):
    """Sync project associations."""
    if not os.path.exists(PROJECT_MAP_CSV):
        logger.warning(f"Could not find {PROJECT_MAP_CSV}")
        return

    logger.info("Syncing ZenTao project/execution links...")
    with open(PROJECT_MAP_CSV, encoding="utf-8-sig") as f:
        lines = [line for line in f if not line.strip().startswith("#")]
        reader = csv.DictReader(lines)
        for row in reader:
            try:
                zt_ref = row.get("zentao_execution_id", "").strip()
                zt_name = row.get("zentao_execution_name", "").strip()
                mdm_ref = row.get("mdm_project_id", "").strip()

                if not mdm_ref:
                    continue

                # Batch commit to prevent huge locks
                if reader.line_num % 20 == 0:
                    session.commit()

                # Find MDM Project
                mdm_project = (
                    session.query(ProjectMaster)
                    .filter(
                        (ProjectMaster.project_id == mdm_ref)
                        | (ProjectMaster.project_id == f"PROJ-{mdm_ref}")
                        | (ProjectMaster.project_name == mdm_ref)
                        | (ProjectMaster.project_name == zt_name)
                    )
                    .first()
                )

                if not mdm_project:
                    logger.warning(f"Skip: MDM Project not found (Ref={mdm_ref})")
                    continue

                # Find ZenTao Execution Node
                target_node = None
                if zt_ref.isdigit():
                    target_node = session.query(ZenTaoExecution).filter_by(id=int(zt_ref)).first()
                if not target_node:
                    target_node = session.query(ZenTaoExecution).filter((ZenTaoExecution.code == zt_ref) | (ZenTaoExecution.name == zt_name)).first()

                if target_node:
                    target_node.mdm_project_id = mdm_project.project_id

                    # Inheritance
                    search_pattern = f"%,{target_node.id},%"
                    children = session.query(ZenTaoExecution).filter(ZenTaoExecution.path.like(search_pattern), ZenTaoExecution.id != target_node.id).all()
                    for child in children:
                        child.mdm_project_id = mdm_project.project_id

                    topology = (
                        session.query(EntityTopology)
                        .filter_by(system_code="zentao-prod", external_resource_id=str(target_node.id), element_type="issue-tracker")
                        .first()
                    )
                    if not topology:
                        topology = EntityTopology(
                            system_code="zentao-prod",
                            external_resource_id=str(target_node.id),
                            resource_name=target_node.name,
                            element_type="issue-tracker",
                            is_active=True,
                            sync_version=1,
                        )
                        session.add(topology)
                    topology.project_id = mdm_project.project_id
                    session.flush()
                    logger.info(f"Linked Project: ZenTao Node '{target_node.name}' -> MDM '{mdm_project.project_name}'")
                else:
                    # Strategy B: If Ref matches a Product, link all its executions to this MDM Project
                    zt_product = session.query(ZenTaoProduct).filter((ZenTaoProduct.code == zt_ref) | (ZenTaoProduct.name == zt_name)).first()
                    if zt_product:
                        product_executions = session.query(ZenTaoExecution).filter_by(product_id=zt_product.id).all()
                        if product_executions:
                            for exec_node in product_executions:
                                exec_node.mdm_project_id = mdm_project.project_id
                                topology = (
                                    session.query(EntityTopology)
                                    .filter_by(system_code="zentao-prod", external_resource_id=str(exec_node.id), element_type="issue-tracker")
                                    .first()
                                )
                                if not topology:
                                    topology = EntityTopology(
                                        system_code="zentao-prod",
                                        external_resource_id=str(exec_node.id),
                                        resource_name=exec_node.name,
                                        element_type="issue-tracker",
                                        is_active=True,
                                        sync_version=1,
                                    )
                                    session.add(topology)
                                topology.project_id = mdm_project.project_id
                            session.flush()
                            logger.info(f"Linked Product-level Project: ZenTao Product '{zt_product.name}' -> MDM '{mdm_project.project_name}'")
                        else:
                            logger.warning(f"Skip: Found ZenTao Product '{zt_product.name}' but no executions found.")
                    else:
                        logger.warning(f"Could not find ZenTao execution or product: Ref={zt_ref}, Name={zt_name}")
            except Exception as e:
                session.rollback()
                logger.error(f"Row error (Project: {row}): {e}")


def main():
    engine = create_engine(settings.database.uri)
    ensure_system_registry(Session(engine))

    with Session(engine) as session:
        try:
            init_product_links(session)
            init_project_links(session)
            session.commit()
            logger.info("ZenTao links initialized!")
        except Exception as e:
            session.rollback()
            logger.error(f"Sync failed: {e}")
            raise


if __name__ == "__main__":
    main()

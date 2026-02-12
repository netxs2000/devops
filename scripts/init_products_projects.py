"""初始化产品与项目主数据。

本脚本已重构为从 docs/products.csv 和 docs/projects.csv 动态加载。
"""
import sys
import os
import logging
import uuid
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import Base, Organization, Product, ProjectMaster, ProjectProductRelation, User

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PRD_CSV = Path(__file__).parent.parent / 'docs' / 'products.csv'
PROJ_CSV = Path(__file__).parent.parent / 'docs' / 'projects.csv'

def init_products(session: Session):
    if not PRD_CSV.exists(): return {}
    logger.info('同步产品主数据...')
    prod_map = {}
    with open(PRD_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row['产品名称'].strip()
            prod_id = f"PRD-{uuid.uuid5(uuid.NAMESPACE_DNS, name).hex[:8].upper()}"
            product = session.query(Product).filter_by(product_name=name).first()
            if not product:
                product = Product(product_id=prod_id, product_name=name, lifecycle_status='Active')
                session.add(product)
            session.flush()
            prod_map[name] = product.product_id
    session.commit()
    return prod_map

def init_projects(session: Session, prod_map):
    if not PROJ_CSV.exists(): return
    logger.info('同步项目主数据...')
    with open(PROJ_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code, name, prod_name = row['项目代号'].strip(), row['项目名称'].strip(), row['所属产品'].strip()
            proj_id = f"PROJ-{code}"
            project = session.query(ProjectMaster).filter_by(project_id=proj_id).first()
            if not project:
                project = ProjectMaster(project_id=proj_id, project_name=name, status='ACTIVE', is_current=True)
                session.add(project)
            session.flush()
            # 建立关联
            target_prod_id = prod_map.get(prod_name)
            if target_prod_id:
                rel = session.query(ProjectProductRelation).filter_by(project_id=proj_id, product_id=target_prod_id).first()
                if not rel:
                    session.add(ProjectProductRelation(project_id=proj_id, product_id=target_prod_id, relation_type='PRIMARY'))
    session.commit()

def main():
    engine = create_engine(settings.database.uri)
    with Session(engine) as session:
        pm = init_products(session)
        init_projects(session, pm)

if __name__ == '__main__':
    main()

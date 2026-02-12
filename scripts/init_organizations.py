"""初始化组织架构及负责人数据。

本脚本已重构为从 docs/organizations.csv 动态加载数据，不再包含任何硬编码。
执行方式:
    python scripts/init_organizations.py
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
from devops_collector.models import Base, Organization, User

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_FILE = Path(__file__).parent.parent / 'docs' / 'organizations.csv'

def init_organizations_from_csv(session: Session):
    """从 CSV 文件加载组织架构。"""
    if not CSV_FILE.exists():
        logger.warning(f"跳过组织初始化：找不到 CSV 文件 {CSV_FILE}")
        return

    logger.info(f'开始从 {CSV_FILE} 同步组织架构...')
    
    with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            system = row.get('体系', '').strip()
            center = row.get('中心', '').strip()
            dept = row.get('部门', '').strip()
            manager_name = row.get('负责人', '').strip()

            # 逻辑：逐级建立组织
            parent_id = None
            
            # 1. 体系层级 (L1)
            if system:
                org_id_l1 = f"SYS-{system}"
                org_l1 = session.query(Organization).filter_by(org_id=org_id_l1).first()
                if not org_l1:
                    org_l1 = Organization(org_id=org_id_l1, org_name=system, org_level=1)
                    session.add(org_l1)
                parent_id = org_id_l1
            
            # 2. 中心层级 (L2)
            if center:
                org_id_l2 = f"CTR-{center}"
                org_l2 = session.query(Organization).filter_by(org_id=org_id_l2).first()
                if not org_l2:
                    org_l2 = Organization(org_id=org_id_l2, org_name=center, org_level=2, parent_org_id=parent_id)
                    session.add(org_l2)
                parent_id = org_id_l2
                
            # 3. 部门层级 (L3)
            if dept:
                org_id_l3 = f"DEP-{dept}"
                org_l3 = session.query(Organization).filter_by(org_id=org_id_l3).first()
                if not org_l3:
                    org_l3 = Organization(org_id=org_id_l3, org_name=dept, org_level=3, parent_org_id=parent_id)
                    session.add(org_l3)
    
    session.commit()
    logger.info("组织架构同步完成！")

def main():
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        init_organizations_from_csv(session)

if __name__ == '__main__':
    main()

"""服务目录初始化脚本。

重构：从 docs/service_catalog.csv 加载。
"""
import os
import sys
import logging
import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.append(os.getcwd())
from devops_collector.config import settings
from devops_collector.models.base_models import Base, Service, ServiceProjectMapping, Organization

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_FILE = 'docs/service_catalog.csv'

def init_catalog():
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        if not os.path.exists(CSV_FILE): return
        logger.info(f'从 {CSV_FILE} 同步服务目录...')
        
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['服务名称'].strip()
                org_name = row['所属组织'].strip()
                org = session.query(Organization).filter_by(org_name=org_name).first()
                if not org:
                    logger.warning(f"组织 {org_name} 不存在，跳过 {name}")
                    continue
                
                service = session.query(Service).filter_by(name=name).first()
                if not service:
                    service = Service(name=name)
                    session.add(service)
                service.tier = row['服务分级']
                service.description = row['描述']
                service.org_id = org.org_id
                session.flush()
                
                # 处理项目映射 (简单版本)
                projects = [p.strip() for p in row['关联项目路径'].split(',')]
                # 这里目前仅作为示例逻辑记录，后续可与插件表联动
        session.commit()

if __name__ == '__main__':
    init_catalog()
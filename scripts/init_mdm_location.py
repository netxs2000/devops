"""创建 MDM_LOCATION 表并初始化省份主数据。

重构：从 docs/locations.csv 加载。
"""
import sys
import os
import logging
import csv
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import Base, Location

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CSV_FILE = 'docs/locations.csv'

def init_mdm_location():
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine, tables=[Location.__table__])
    
    if not os.path.exists(CSV_FILE): return
    logger.info(f'从 {CSV_FILE} 加载地理位置...')
    
    with Session(engine) as session, open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            loc_id = row['ID'].strip()
            loc = session.query(Location).filter_by(location_id=loc_id).first()
            if not loc:
                loc = Location(location_id=loc_id)
                session.add(loc)
            loc.location_name = row['全称']
            loc.short_name = row['名称']
            loc.region = row['大区']
            loc.code = row['编码']
            loc.location_type = 'province' if loc_id != '000000' else 'region'
            loc.is_active = True
        session.commit()
    logger.info("地理位置初始化完成。")

if __name__ == '__main__':
    init_mdm_location()
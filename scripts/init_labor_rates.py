"""人工费率表初始化。

重构：从 docs/labor_rates.csv 导入。
"""
import os
import sys
import logging
import csv
from datetime import datetime, timezone
sys.path.append(os.getcwd())
from devops_collector.config import settings
from devops_collector.models.base_models import Base, LaborRateConfig
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_FILE = 'docs/labor_rates.csv'

def init_labor_rates():
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        if not os.path.exists(CSV_FILE): return
        logger.info(f'从 {CSV_FILE} 加载费率...')
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                level = row['职级'].strip()
                rate = float(row['日费率'])
                obj = session.query(LaborRateConfig).filter_by(job_title_level=level, is_active=True).first()
                if not obj:
                    obj = LaborRateConfig(job_title_level=level)
                    session.add(obj)
                obj.daily_rate = rate
                obj.hourly_rate = rate / 8.0
                obj.currency = 'CNY'
                obj.effective_date = datetime.now(timezone.utc)
            session.commit()

if __name__ == '__main__':
    init_labor_rates()
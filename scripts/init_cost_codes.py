"""财务成本科目 (CBS) 初始化脚本。

重构：从 docs/cost_codes.csv 导入。
"""
import csv
import logging
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


sys.path.append(os.getcwd())
from devops_collector.config import settings
from devops_collector.models.base_models import Base, CostCode


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_FILE = 'docs/cost_codes.csv'

def init_cost_codes():
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if not os.path.exists(CSV_FILE): return
        logger.info(f'从 {CSV_FILE} 加载成本科目...')

        with open(CSV_FILE, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row['科目代码'].strip()
                cc = session.query(CostCode).filter_by(code=code).first()
                if not cc:
                    cc = CostCode(code=code)
                    session.add(cc)
                cc.name = row['科目名称']
                cc.category = row['分类']
                cc.default_capex_opex = row['支出类型']
                cc.description = row['描述']

                # 处理父级
                parent_code = row.get('父级代码')
                if parent_code:
                    parent = session.query(CostCode).filter_by(code=parent_code).first()
                    if parent: cc.parent_id = parent.id

                session.flush()
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"失败: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    init_cost_codes()

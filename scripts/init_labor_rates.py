"""人工费率表 (Blended Rate) 初始化脚本。

用于定义不同岗位级别（Job Level）的标准人工成本。
系统将使用此表通过岗位等级计算人工成本，而非使用真实的员工薪资，从而保护员工隐私。

使用方法:
1. 在 LABOR_RATES 数据结构中定义您的费率标准。
2. 运行: python scripts/init_labor_rates.py
"""
import os
import sys
import logging
from datetime import datetime, timezone
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devops_collector.config import get_config
from devops_collector.models.base_models import Base, LaborRateConfig
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
LABOR_RATES = [{'level': 'P1/T1', 'daily_rate': 800.0, 'desc': '初级 (Junior)'}, {'level': 'P2/T2', 'daily_rate': 1200.0, 'desc': '中级 (Middle)'}, {'level': 'P3/T3', 'daily_rate': 1800.0, 'desc': '高级 (Senior)'}, {'level': 'P4/T4', 'daily_rate': 2500.0, 'desc': '资深 (Expert)'}, {'level': 'P5/T5', 'daily_rate': 3500.0, 'desc': '架构师/专家 (Principal)'}, {'level': 'M1', 'daily_rate': 2000.0, 'desc': '基层管理 (Manager)'}, {'level': 'M2', 'daily_rate': 3000.0, 'desc': '中层管理 (Director)'}]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_labor_rates():
    """初始化组织级的人工标准费率表 (Blended Rates)。

    建立职级与标准人天成本的映射关系，为 FinOps 成本分摊提供计算依据。
    """
    config = get_config()
    db_uri = config.get('database', 'uri')
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        logger.info('开始初始化人工费率表 (Blended Rates)...')
        for rate_data in LABOR_RATES:
            level = rate_data['level']
            rate = rate_data['daily_rate']
            obj = session.query(LaborRateConfig).filter(LaborRateConfig.job_title_level == level, LaborRateConfig.is_active == True).first()
            if not obj:
                obj = LaborRateConfig(job_title_level=level)
                session.add(obj)
                logger.info(f'添加费率: {level} -> {rate}/天')
            else:
                logger.info(f'更新费率: {level} -> {rate}/天')
            obj.daily_rate = rate
            obj.hourly_rate = rate / 8.0
            obj.currency = 'CNY'
            obj.effective_date = datetime.now(timezone.utc)
        session.commit()
        logger.info('人工费率表初始化完成！')
    except Exception as e:
        session.rollback()
        logger.error(f'发生错误: {e}')
        raise
    finally:
        session.close()
if __name__ == '__main__':
    init_labor_rates()
"""日历与时间维度主数据 (MDM_CALENDAR) 初始化脚本。

本脚本执行以下操作:
1. 确保 mdm_calendar 表已创建。
2. 批量生成指定年份范围（如 2015-2030）的基础日历数据。
3. 自动标记周末为非工作日。
4. 预置 2025 年中国法定节假日与调休安排（示例）。

执行方式:
    python scripts/init_calendar.py
"""
import os
import sys
import logging
from datetime import date, timedelta, datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devops_collector.config import settings
from devops_collector.models.base_models import Base, Calendar
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
HOLIDAYS_2025 = {date(2025, 1, 1): '元旦', date(2025, 1, 28): '除夕', date(2025, 1, 29): '春节', date(2025, 1, 30): '初二', date(2025, 1, 31): '初三', date(2025, 2, 1): '初四', date(2025, 2, 2): '初五', date(2025, 2, 3): '初六', date(2025, 2, 4): '初七', date(2025, 4, 4): '清明节', date(2025, 4, 5): '清明假期', date(2025, 4, 6): '清明假期', date(2025, 5, 1): '劳动节', date(2025, 5, 2): '劳动假期', date(2025, 5, 3): '劳动假期', date(2025, 5, 4): '劳动假期', date(2025, 5, 5): '劳动假期', date(2025, 5, 31): '端午节', date(2025, 6, 1): '端午假期', date(2025, 6, 2): '端午假期', date(2025, 10, 1): '国庆节', date(2025, 10, 2): '国庆假期', date(2025, 10, 3): '国庆假期', date(2025, 10, 4): '中秋节', date(2025, 10, 5): '国庆假期', date(2025, 10, 6): '国庆假期', date(2025, 10, 7): '国庆假期', date(2025, 10, 8): '国庆假期'}
WORKDAYS_2025 = {date(2025, 1, 26): '春节调休补班', date(2025, 2, 8): '春节调休补班', date(2025, 4, 27): '劳动节调休补班', date(2025, 9, 28): '国庆调休补班', date(2025, 10, 11): '国庆调休补班'}

def get_fiscal(d: date):
    """计算财年和财季 (假设财年等于公历年)。"""
    year = d.year
    quarter = (d.month - 1) // 3 + 1
    return (f'FY{year}', f'FY{str(year)[2:]}Q{quarter}')

def init_calendar(start_year=2015, end_year=2030):
    """初始化日历表数据。"""
    db_uri = settings.database.uri
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        logger.info(f'正在初始化日历数据从 {start_year} 到 {end_year}...')
        current_date = date(start_year, 1, 1)
        end_date = date(end_year, 12, 31)
        count = 0
        while current_date <= end_date:
            exists = session.query(Calendar).filter_by(date_day=current_date).first()
            if not exists:
                weekday = current_date.isoweekday()
                week_of_year = current_date.isocalendar()[1]
                fiscal_year, fiscal_quarter = get_fiscal(current_date)
                is_weekend = weekday >= 6
                is_workday = not is_weekend
                is_holiday = False
                h_name = None
                if current_date in HOLIDAYS_2025:
                    is_holiday = True
                    is_workday = False
                    h_name = HOLIDAYS_2025[current_date]
                elif current_date in WORKDAYS_2025:
                    is_workday = True
                    is_holiday = False
                    h_name = WORKDAYS_2025[current_date]
                cal = Calendar(date_day=current_date, year_number=current_date.year, month_number=current_date.month, quarter_number=(current_date.month - 1) // 3 + 1, day_of_week=weekday, is_workday=is_workday, is_holiday=is_holiday, holiday_name=h_name, fiscal_year=fiscal_year, fiscal_quarter=fiscal_quarter, week_of_year=week_of_year, season_tag=None)
                session.add(cal)
                count += 1
                if count % 1000 == 0:
                    session.flush()
                    logger.info(f'已处理 {count} 天...')
            current_date += timedelta(days=1)
        session.commit()
        logger.info(f'✅ 日历初始化成功，共插入 {count} 条新记录。')
    except Exception as e:
        session.rollback()
        logger.error(f'❌ 发生错误: {e}')
        raise
    finally:
        session.close()
if __name__ == '__main__':
    init_calendar()
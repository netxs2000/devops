"""采购合同 (Purchase Contract) 初始化脚本。

重构说明：已移除硬编码 SAMPLE_PURCHASE_CONTRACTS，改为从 docs/purchase_contracts.csv 加载。
"""
import csv
import logging
import os
import sys
from datetime import datetime


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from devops_collector.config import settings
from devops_collector.models.base_models import Base, CostCode, PurchaseContract, ResourceCost


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_FILE = os.path.join('docs', 'purchase_contracts.csv')

def init_purchase_contracts():
    db_uri = settings.database.uri
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if not os.path.exists(CSV_FILE):
            logger.warning(f"跳过采购合同初始化：未找到 {CSV_FILE}")
            return

        logger.info(f'开始从 {CSV_FILE} 录入采购合同数据...')

        with open(CSV_FILE, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                contract_no = row['合同编号'].strip()
                title = row['合同标题'].strip()
                vendor = row['供应商名称'].strip()
                vendor_id = row['供应商ID'].strip()
                total = float(row['总金额'])
                start_date = datetime.strptime(row['开始日期'].strip(), '%Y-%m-%d')
                end_date = datetime.strptime(row['结束日期'].strip(), '%Y-%m-%d')
                cost_code = row['科目代码'].strip()
                capex_opex = row['支出类型'].strip()

                cc = session.query(CostCode).filter(CostCode.code == cost_code).first()
                if not cc:
                    logger.warning(f"找不到科目代码 {cost_code}，请先初始化科目。")
                    continue

                pc = session.query(PurchaseContract).filter(PurchaseContract.contract_no == contract_no).first()
                if not pc:
                    pc = PurchaseContract(contract_no=contract_no)
                    session.add(pc)
                    logger.info(f"录入采购合同: [{contract_no}] {title}")

                pc.title = title
                pc.vendor_name = vendor
                pc.vendor_id = vendor_id
                pc.total_amount = total
                pc.start_date = start_date
                pc.end_date = end_date
                pc.cost_code_id = cc.id
                pc.capex_opex_flag = capex_opex
                session.flush()

                # 生成演示流水 (2025-01)
                period = '2025-01'
                cost_record = session.query(ResourceCost).filter(ResourceCost.purchase_contract_id == pc.id, ResourceCost.period == period).first()
                if not cost_record:
                    monthly_amount = pc.total_amount / 12.0
                    cost_record = ResourceCost(
                        purchase_contract_id=pc.id, period=period,
                        cost_type=cc.category, cost_item=pc.title,
                        amount=monthly_amount, currency=pc.currency,
                        capex_opex_flag=pc.capex_opex_flag, vendor_name=pc.vendor_name,
                        cost_code_id=cc.id, source_system='contract_system_init'
                    )
                    session.add(cost_record)
                    logger.info(f'  -> 已生成 {period} 摊销流水: {monthly_amount:.2f}')

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f'录入失败: {e}')
        raise
    finally:
        session.close()

if __name__ == '__main__':
    init_purchase_contracts()

"""采购合同 (Purchase Contract) 初始化脚本。

演示如何录入采购合同（如云服务、外包人力），并将其关联到特定的财务科目。
同时演示如何基于合同生成初始的成本流水。

使用方法:
1. 修改 SAMPLE_PURCHASE_CONTRACTS 数据。
2. 运行: python scripts/init_purchase_contracts.py
"""
import os
import sys
import logging
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devops_collector.config import settings
from devops_collector.models.base_models import Base, PurchaseContract, CostCode, ResourceCost
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
SAMPLE_PURCHASE_CONTRACTS = [{'contract_no': 'PUR-2025-AWS-001', 'title': 'AWS 核心生产环境年度认购', 'vendor_name': 'Amazon Web Services', 'vendor_id': 'VEND_AWS_001', 'total_amount': 1200000.0, 'start_date': datetime(2025, 1, 1), 'end_date': datetime(2025, 12, 31), 'cost_code_match': '1002.01', 'capex_opex': 'OPEX'}, {'contract_no': 'PUR-2025-OUT-102', 'title': '2025年度交付外包框架合同', 'vendor_name': '某动力信息技术有限公司', 'vendor_id': 'VEND_SOFT_102', 'total_amount': 3000000.0, 'start_date': datetime(2025, 1, 1), 'end_date': datetime(2025, 12, 31), 'cost_code_match': '1001.03', 'capex_opex': 'OPEX'}]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_purchase_contracts():
    """初始化示例采购合同元数据，并演示月初线性摊销成本流水生产。

    涵盖了云服务认购、外包人力框架合同等典型场景。
    """
    db_uri = settings.database.uri
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        logger.info('开始录入采购合同元数据...')
        for data in SAMPLE_PURCHASE_CONTRACTS:
            cc = session.query(CostCode).filter(CostCode.code == data['cost_code_match']).first()
            if not cc:
                logger.warning(f"找不到科目代码 {data['cost_code_match']}，请先运行 init_cost_codes.py")
                continue
            pc = session.query(PurchaseContract).filter(PurchaseContract.contract_no == data['contract_no']).first()
            if not pc:
                pc = PurchaseContract(contract_no=data['contract_no'])
                session.add(pc)
                logger.info(f"录入采购合同: [{pc.contract_no}] {data['title']}")
            pc.title = data['title']
            pc.vendor_name = data['vendor_name']
            pc.vendor_id = data['vendor_id']
            pc.total_amount = data['total_amount']
            pc.start_date = data['start_date']
            pc.end_date = data['end_date']
            pc.cost_code_id = cc.id
            pc.capex_opex_flag = data['capex_opex']
            session.flush()
            period = '2025-01'
            cost_record = session.query(ResourceCost).filter(ResourceCost.purchase_contract_id == pc.id, ResourceCost.period == period).first()
            if not cost_record:
                monthly_amount = pc.total_amount / 12.0
                cost_record = ResourceCost(purchase_contract_id=pc.id, period=period, cost_type=cc.category, cost_item=pc.title, amount=monthly_amount, currency=pc.currency, capex_opex_flag=pc.capex_opex_flag, vendor_name=pc.vendor_name, cost_code_id=cc.id, source_system='contract_system_init')
                session.add(cost_record)
                logger.info(f'  -> 已生成 {period} 摊销流水: {monthly_amount:.2f}')
        session.commit()
        logger.info('采购合同初始化完成！')
    except Exception as e:
        session.rollback()
        logger.error(f'录入失败: {e}')
        raise
    finally:
        session.close()
if __name__ == '__main__':
    init_purchase_contracts()
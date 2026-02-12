"""收入合同初始化脚本。

重构说明：已移除硬编码 SAMPLE_CONTRACT，改为从 docs/revenue_contracts.csv 加载。
"""
import os
import sys
import logging
import csv
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devops_collector.config import settings
from devops_collector.models.base_models import Base, RevenueContract, ContractPaymentNode, Product
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CSV_FILE = os.path.join('docs', 'revenue_contracts.csv')

def init_revenue_contracts():
    db_uri = settings.database.uri
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        if not os.path.exists(CSV_FILE):
            logger.warning(f"跳过收入合同初始化：未找到 {CSV_FILE}")
            return

        logger.info(f'开始从 {CSV_FILE} 录入收入合同数据...')
        
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                contract_no = row['合同编号'].strip()
                title = row['合同标题'].strip()
                client = row['客户名称'].strip()
                total = float(row['总价值'])
                sign_date = datetime.strptime(row['签约日期'].strip(), '%Y-%m-%d')
                prod_name = row['所属产品'].strip()

                product = session.query(Product).filter(Product.product_name == prod_name).first()
                if not product:
                    logger.warning(f"产品 {prod_name} 不存在，将作为独立合同录入。")

                contract = session.query(RevenueContract).filter(RevenueContract.contract_no == contract_no).first()
                if not contract:
                    contract = RevenueContract(contract_no=contract_no)
                    session.add(contract)
                    logger.info(f"录入新合同: {contract_no}")
                
                contract.title = title
                contract.client_name = client
                contract.total_value = total
                contract.sign_date = sign_date
                if product:
                    contract.product_id = product.product_id
                
                # 默认创建一个首付款节点 (30%)
                session.flush()
                session.query(ContractPaymentNode).filter(ContractPaymentNode.contract_id == contract.id).delete()
                billing_amount = contract.total_value * 0.3
                node = ContractPaymentNode(
                    contract_id=contract.id, 
                    node_name='首付款 (Down Payment)', 
                    billing_percentage=30.0, 
                    billing_amount=billing_amount, 
                    linked_system='manual',
                    is_achieved=False
                )
                session.add(node)
                logger.info(f'  -> 自动生成首付款阶段: 金额 {billing_amount}')

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f'录入失败: {e}')
        raise
    finally:
        session.close()

if __name__ == '__main__':
    init_revenue_contracts()
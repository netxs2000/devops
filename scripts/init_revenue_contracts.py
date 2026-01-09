"""收入合同及收款节点 (3-4-3) 初始化脚本。

演示如何将一份价值 100 万的合同拆分为 30%, 40%, 30% 三个收款阶段，
并将其与技术系统的里程碑进行联动绑定。

使用方法:
1. 修改脚本中的 SAMPLE_CONTRACT 数据。
2. 运行: python scripts/init_revenue_contracts.py
"""
import os
import sys
import logging
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devops_collector.config import settings
from devops_collector.models.base_models import Base, RevenueContract, ContractPaymentNode, Product
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
SAMPLE_CONTRACT = {'contract_no': 'ABC-SALE-2025-001', 'title': '智慧城市大数据平台建设项目', 'client_name': '某市大数据局', 'total_value': 1000000.0, 'sign_date': datetime(2025, 1, 1), 'product_name': '大数据底座', 'nodes': [{'name': '首付款 (Down Payment)', 'percentage': 30.0, 'linked_system': 'manual', 'is_achieved': True, 'achieved_at': datetime(2025, 1, 5)}, {'name': '交付验收款 (UAT Acceptance)', 'percentage': 40.0, 'linked_system': 'gitlab', 'linked_milestone_id': 101, 'is_achieved': False}, {'name': '质保尾款 (Final Acceptance)', 'percentage': 30.0, 'linked_system': 'gitlab', 'linked_milestone_id': 102, 'is_achieved': False}]}
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_revenue_contracts():
    """初始化示例收入合同及其 3-4-3 收款分阶段计划。

    演示如何将技术里程碑 (GitLab Milestone) 的状态与财务回款节点进行对齐。
    """
    db_uri = settings.database.uri
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        logger.info('开始录入收入合同及 3-4-3 收款节点...')
        product = session.query(Product).filter(Product.product_name == SAMPLE_CONTRACT['product_name']).first()
        if not product:
            logger.warning(f"产品 {SAMPLE_CONTRACT['product_name']} 不存在，将作为独立合同录入。")
        contract = session.query(RevenueContract).filter(RevenueContract.contract_no == SAMPLE_CONTRACT['contract_no']).first()
        if not contract:
            contract = RevenueContract(contract_no=SAMPLE_CONTRACT['contract_no'])
            session.add(contract)
            logger.info(f"录入新合同: {SAMPLE_CONTRACT['contract_no']}")
        contract.title = SAMPLE_CONTRACT['title']
        contract.client_name = SAMPLE_CONTRACT['client_name']
        contract.total_value = SAMPLE_CONTRACT['total_value']
        contract.sign_date = SAMPLE_CONTRACT['sign_date']
        if product:
            contract.product_id = product.product_id
        session.flush()
        session.query(ContractPaymentNode).filter(ContractPaymentNode.contract_id == contract.id).delete()
        for node_data in SAMPLE_CONTRACT['nodes']:
            billing_amount = contract.total_value * (node_data['percentage'] / 100.0)
            node = ContractPaymentNode(contract_id=contract.id, node_name=node_data['name'], billing_percentage=node_data['percentage'], billing_amount=billing_amount, linked_system=node_data['linked_system'], linked_milestone_id=node_data.get('linked_milestone_id'), is_achieved=node_data.get('is_achieved', False), achieved_at=node_data.get('achieved_at'))
            session.add(node)
            status = ' [已达成] ' if node.is_achieved else ' [进行中] '
            logger.info(f'  -> 创建收款阶段: {node.node_name} ({node.billing_percentage}%), 金额: {node.billing_amount}{status}')
        session.commit()
        logger.info(f"合同 {SAMPLE_CONTRACT['contract_no']} 及其 3-4-3 支付计划录入完成！")
    except Exception as e:
        session.rollback()
        logger.error(f'录入失败: {e}')
        raise
    finally:
        session.close()
if __name__ == '__main__':
    init_revenue_contracts()
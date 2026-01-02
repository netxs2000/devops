"""财务成本科目 (CBS) 初始化脚本。

用于定义组织级的财务核算科目树。
这支持研发效能度量中的 FinOps 分析和研发资本化审计。

使用方法:
1. 在 COST_CODE_STRUCTURE 数据结构中定义或修改您的会计科目。
2. 运行: python scripts/init_cost_codes.py
"""
import os
import sys
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devops_collector.config import get_config
from devops_collector.models.base_models import Base, CostCode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
COST_CODE_STRUCTURE = [{'code': '1001', 'name': '人力成本 (Labor)', 'category': 'Labor', 'description': '包含内部员工与外包人员的工资及福利支付。', 'children': [{'code': '1001.01', 'name': '核心研发人工 (Internal)', 'category': 'Labor', 'capex_opex': 'CAPEX'}, {'code': '1001.02', 'name': '日常运维人工 (Ops)', 'category': 'Labor', 'capex_opex': 'OPEX'}, {'code': '1001.03', 'name': '研发外包费 (Outsourced)', 'category': 'Labor', 'capex_opex': 'OPEX'}]}, {'code': '1002', 'name': '基础设施与云服务 (Infra)', 'category': 'Infrastructure', 'description': '涵盖云厂商账单、机房租赁及网络带宽费用。', 'children': [{'code': '1002.01', 'name': '云计算节点 (EC2/CVM)', 'category': 'Cloud', 'capex_opex': 'OPEX'}, {'code': '1002.02', 'name': '数据库与存储记录 (DB/OSS)', 'category': 'Cloud', 'capex_opex': 'OPEX'}, {'code': '1002.03', 'name': '安全与CDN加速', 'category': 'Cloud', 'capex_opex': 'OPEX'}]}, {'code': '2001', 'name': '软件资产与授权 (License)', 'category': 'License', 'description': '开发工具、质量门禁工具及中间件授权。', 'children': [{'code': '2001.01', 'name': 'DevOps 工具链授权 (Jira/Sonar)', 'category': 'License', 'capex_opex': 'OPEX'}, {'code': '2001.02', 'name': '第三方库/专利费', 'category': 'License', 'capex_opex': 'CAPEX'}]}]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_node(session, node_data, parent_id=None):
    """递归处理并初始化成本科目节点。

    Args:
        session: SQLAlchemy 会话实例。
        node_data: 包含科目信息的字典，支持嵌套 children。
        parent_id: 父级科目的自增 ID (可选)。
    """
    code = node_data['code']
    name = node_data['name']
    cc = session.query(CostCode).filter(CostCode.code == code).first()
    if not cc:
        cc = CostCode(code=code)
        session.add(cc)
        logger.info(f'创建新科目: [{code}] {name}')
    else:
        logger.info(f'更新已有科目: [{code}] {name}')
    cc.name = name
    cc.description = node_data.get('description')
    cc.category = node_data.get('category')
    cc.default_capex_opex = node_data.get('capex_opex')
    cc.parent_id = parent_id
    cc.is_active = True
    session.flush()
    for child in node_data.get('children', []):
        process_node(session, child, cc.id)

def init_cost_codes():
    """初始化财务成本科目树 (CBS) 的主入口函数。

    负责读取配置、创建表结构并执行递归导入。
    """
    config = get_config()
    db_uri = config.get('database', 'uri')
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        logger.info('开始初始化财务成本科目 (CBS)...')
        for root_node in COST_CODE_STRUCTURE:
            process_node(session, root_node)
        session.commit()
        logger.info('财务科目初始化完成！')
    except Exception as e:
        session.rollback()
        logger.error(f'发生错误: {e}')
        raise
    finally:
        session.close()
if __name__ == '__main__':
    init_cost_codes()
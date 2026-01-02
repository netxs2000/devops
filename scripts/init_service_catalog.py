"""服务目录初始化脚本。

用于手动定义业务服务并将其映射到具体的技术项目（如 GitLab 仓库）。
这是支撑 DevOps 成熟度 L4 度量的基础配置。

使用方法:
1. 在 SERVICE_CATALOG 数据结构中修改您的服务定义。
2. 运行: python scripts/init_service_catalog.py
"""
import os
import sys
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devops_collector.config import get_config
from devops_collector.models.base_models import Base, Service, ServiceProjectMapping, SLO, Organization
from devops_collector.plugins.gitlab.models import Project
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
SERVICE_CATALOG = [{'name': '用户中心 (User Center)', 'tier': 'P0', 'org_name': '研发中心/核心业务部', 'description': '负责全站用户账号、OAuth 鉴权及基础信息管理。', 'projects': ['platform/user-api', 'platform/user-service'], 'slos': [{'name': '可用性 (Availability)', 'type': 'Availability', 'target': 99.9, 'unit': '%'}, {'name': '响应延迟 (Latency P99)', 'type': 'Latency', 'target': 200, 'unit': 'ms'}]}, {'name': '订单系统 (Order System)', 'tier': 'P0', 'org_name': '研发中心/核心业务部', 'description': '负责交易下单、状态机流转及库存扣减逻辑。', 'projects': ['order-center/order-manager'], 'slos': [{'name': '可用性 (Availability)', 'type': 'Availability', 'target': 99.95, 'unit': '%'}]}]
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_catalog():
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    config = get_config()
    db_uri = config.get('database', 'uri')
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        logger.info('开始初始化服务目录...')
        for s_data in SERVICE_CATALOG:
            org = session.query(Organization).filter(Organization.name == s_data['org_name']).first()
            if not org:
                logger.warning(f"组织 {s_data['org_name']} 不存在，跳过该服务。请先确保组织架构已同步。")
                continue
            service = session.query(Service).filter(Service.name == s_data['name']).first()
            if not service:
                service = Service(name=s_data['name'])
                session.add(service)
            service.tier = s_data['tier']
            service.description = s_data['description']
            service.organization_id = org.id
            session.flush()
            session.query(ServiceProjectMapping).filter(ServiceProjectMapping.service_id == service.id).delete()
            for p_path in s_data['projects']:
                project = session.query(Project).filter(Project.path_with_namespace == p_path).first()
                if project:
                    mapping = ServiceProjectMapping(service_id=service.id, source='gitlab', project_id=project.id)
                    session.add(mapping)
                    logger.info(f'已绑定服务 [{service.name}] -> 项目 [{p_path}]')
                else:
                    logger.warning(f'找不到项目路径: {p_path}，请确认该项目是否已采集。')
            session.query(SLO).filter(SLO.service_id == service.id).delete()
            for slo_data in s_data.get('slos', []):
                new_slo = SLO(service_id=service.id, name=slo_data['name'], indicator_type=slo_data['type'], target_value=slo_data['target'], metric_unit=slo_data['unit'], time_window='28d')
                session.add(new_slo)
                logger.info(f"已创建 SLO [{slo_data['name']}] -> 目标 [{slo_data['target']}{slo_data['unit']}]")
        session.commit()
        logger.info('服务目录初始化完成！')
    except Exception as e:
        session.rollback()
        logger.error(f'初始化失败: {e}')
        raise
    finally:
        session.close()
if __name__ == '__main__':
    init_catalog()
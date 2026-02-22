"""初始化系统注册表和服务目录。

从 `docs/mdm_systems_registry.csv` 和 `docs/mdm_services.csv` 加载数据。
"""
import csv
import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import BusinessSystem, Organization, Service, SystemRegistry


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SYSTEMS_CSV = Path(__file__).parent.parent / 'docs' / 'mdm_systems_registry.csv'
SERVICES_CSV = Path(__file__).parent.parent / 'docs' / 'mdm_services.csv'

def ensure_business_system(session: Session, code: str) -> BusinessSystem:
    if not code: return None
    system = session.query(BusinessSystem).filter_by(code=code).first()
    if not system:
        system = BusinessSystem(code=code, name=code, description=f"Auto-created from Service Catalog: {code}")
        session.add(system)
        session.flush()
    return system

def init_systems(session: Session):
    if not SYSTEMS_CSV.exists():
        logger.warning(f"系统注册表文件不存在: {SYSTEMS_CSV}")
        return

    logger.info(f"正在从 {SYSTEMS_CSV.name} 同步系统注册表...")
    with open(SYSTEMS_CSV, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get('system_code', '').strip()
            if not code: continue

            system = session.query(SystemRegistry).filter_by(system_code=code).first()
            if not system:
                system = SystemRegistry(system_code=code, system_name=row.get('system_name', code))
                session.add(system)

            system.system_name = row.get('system_name', code)
            system.system_type = row.get('system_type', '').strip()
            system.env_tag = row.get('env_tag', 'PROD').strip()
            system.base_url = row.get('base_url', '').strip()
            system.api_version = row.get('api_version', '').strip()
            system.auth_type = row.get('auth_type', '').strip()

            is_active_str = row.get('is_active', 'TRUE').strip().upper()
            system.is_active = (is_active_str == 'TRUE')

            system.remarks = row.get('remarks', '').strip()

            session.flush()

    session.commit()
    logger.info("系统注册表同步完成")

def init_services(session: Session):
    if not SERVICES_CSV.exists():
        logger.warning(f"服务目录文件不存在: {SERVICES_CSV}")
        return

    logger.info(f"正在从 {SERVICES_CSV.name} 同步服务目录...")

    # 预加载依赖数据
    orgs = {o.org_name: o.org_id for o in session.query(Organization).filter_by(is_current=True).all()}

    with open(SERVICES_CSV, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('服务名称', '').strip()
            if not name: continue

            service = session.query(Service).filter_by(name=name).first()
            if not service:
                service = Service(name=name)
                session.add(service)

            # 基础属性
            service.tier = row.get('服务分级', '').strip()
            service.description = row.get('描述', '').strip()
            service.lifecycle = row.get('生命周期', 'production').strip()
            service.component_type = row.get('组件类型', 'service').strip()

            # 关联组织
            org_name = row.get('负责组织', '').strip()
            if org_name in orgs:
                service.org_id = orgs[org_name]

            # 关联业务系统 (Business System)
            bs_code = row.get('所属业务系统代码', '').strip()
            bs = ensure_business_system(session, bs_code)
            if bs:
                service.system_id = bs.id

            session.flush()

    session.commit()
    logger.info("服务目录同步完成")

def main():
    engine = create_engine(settings.database.uri)
    with Session(engine) as session:
        init_systems(session)
        init_services(session)

if __name__ == '__main__':
    main()

"""初始化组织架构主数据 (MDM_ORGANIZATIONS)。

本脚本用于：
1. 创建基础的组织架构树。
2. 为后续的服务目录和成本核算提供基础。

执行方式:
    python scripts/init_organizations.py
"""
import sys
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import Base, Organization

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ORG_STRUCTURE = [
    # root
    {'org_id': 'ORG-ROOT', 'org_name': '某集团公司', 'parent_id': None, 'level': 0},
    # level 1
    {'org_id': 'ORG-RD', 'org_name': '研发中心', 'parent_id': 'ORG-ROOT', 'level': 1},
    {'org_id': 'ORG-OPS', 'org_name': '运维部', 'parent_id': 'ORG-ROOT', 'level': 1},
    # level 2
    {'org_id': 'ORG-CORE-BUS', 'org_name': '研发中心/核心业务部', 'parent_id': 'ORG-RD', 'level': 2},
    {'org_id': 'ORG-INFRA', 'org_name': '研发中心/基础设施组', 'parent_id': 'ORG-RD', 'level': 2},
]

def init_organizations():
    """初始化组织架构。"""
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        logger.info('开始初始化组织架构数据...')
        for org_data in ORG_STRUCTURE:
            existing = session.query(Organization).filter_by(org_id=org_data['org_id']).first()
            if not existing:
                org = Organization(
                    org_id=org_data['org_id'],
                    org_name=org_data['org_name'],
                    org_level=org_data['level'],
                    parent_org_id=org_data['parent_id'],
                    is_active=True,
                    sync_version=1,
                    is_current=True
                )
                session.add(org)
                logger.info(f"已创建组织: {org_data['org_name']} ({org_data['org_id']})")
            else:
                existing.org_name = org_data['org_name']
                existing.parent_org_id = org_data['parent_id']
                existing.org_level = org_data['level']
                logger.info(f"已更新组织: {org_data['org_name']}")
        
        session.commit()
        logger.info('✅ 组织架构初始化完成！')

if __name__ == '__main__':
    init_organizations()

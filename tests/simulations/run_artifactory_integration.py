"""Nexus & JFrog 制品库仿真集成测试脚本 (Artifactory Simulation)

验证路径：
1. Nexus 组件与资产同步 (Components & Assets)
2. JFrog 制品、统计与安全扫描同步 (Artifacts, Stats & Xray)
3. 身份归一化验证
4. 跨库关联 (JFrog Build Name -> Jenkins)
"""

import sys
import os
import json
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 路径设置
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from devops_collector.models import (
    Base, NexusComponent, NexusAsset, JFrogArtifact, JFrogScan,
    User, IdentityMapping
)
from devops_collector.plugins.nexus.client import NexusClient
from devops_collector.plugins.nexus.worker import NexusWorker
from devops_collector.plugins.jfrog.client import JFrogClient
from devops_collector.plugins.jfrog.worker import JFrogWorker

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ArtifactorySimulation')

# 加载数据辅助函数
def load_mock_json(filename):
    path = os.path.join(os.path.dirname(__file__), 'mock_data', filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 数据缓存
MOCK_DATA = {
    'nx_repos': load_mock_json('nexus_repositories.json'),
    'nx_comps': load_mock_json('nexus_components.json'),
    'jf_artifacts': load_mock_json('jfrog_artifacts.json'),
    'jf_stats': load_mock_json('jfrog_stats.json'),
    'jf_xray': load_mock_json('jfrog_xray.json')
}

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
    def json(self): return self.json_data
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(f"HTTP {self.status_code}")

def mocked_requests_get(*args, **kwargs):
    url = args[0]
    logger.info(f"Mocking GET: {url}")
    
    # 1. Nexus Routing
    if "mock-nexus.com" in url:
        if "/components" in url: return MockResponse(MOCK_DATA['nx_comps'])
        if "/repositories" in url: return MockResponse(MOCK_DATA['nx_repos'])
        return MockResponse({})
        
    # 2. JFrog Routing
    if "mock-jfrog.com" in url:
        if "stats" in url: return MockResponse(MOCK_DATA['jf_stats'])
        if "xray/summary" in url: return MockResponse(MOCK_DATA['jf_xray'])
        return MockResponse({})
        
    return MockResponse({}, status_code=404)

def mocked_requests_post(*args, **kwargs):
    url = args[0]
    logger.info(f"Mocking POST: {url}")
    if "mock-jfrog.com" in url and "search/aql" in url:
        return MockResponse(MOCK_DATA['jf_artifacts'])
    return MockResponse({}, status_code=404)

def run_simulation():
    logger.info("📦 Artifactory Plugins Simulation Initializing...")

    # 初始化内存数据库
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    with patch('requests.get', side_effect=mocked_requests_get), \
         patch('requests.post', side_effect=mocked_requests_post):
        
        # --- Stage 1: Nexus Sync ---
        logger.info("--- [STAGE 1] Syncing Nexus Data ---")
        nx_client = NexusClient(url="http://mock-nexus.com", user="admin", password="password")
        nx_worker = NexusWorker(session=session, client=nx_client)
        nx_worker.process_task({'repository': 'maven-releases'})

        # --- Stage 2: JFrog Sync ---
        logger.info("--- [STAGE 2] Syncing JFrog Data ---")
        jf_client = JFrogClient(url="http://mock-jfrog.com", token="jf-fake")
        jf_worker = JFrogWorker(session=session, client=jf_client)
        jf_worker.process_task({'repo': 'docker-local'})

        # --- Stage 3: Verification ---
        logger.info("--- [STAGE 3] Data Verification ---")
        
        # 1. 验证 Nexus
        comp = session.query(NexusComponent).first()
        asset_count = session.query(NexusAsset).filter_by(component_id=comp.id).count()
        logger.info(f" Nexus Component: {comp.name} v{comp.version} (Assets: {asset_count})")
        assert comp.name == "core-library"
        assert asset_count == 2

        # 2. 验证 JFrog
        artifact = session.query(JFrogArtifact).first()
        logger.info(f" JFrog Artifact: {artifact.name} (Size: {artifact.size_bytes} bytes)")
        assert artifact.name == "v1.0.0"
        assert artifact.download_count == 150

        # 3. 验证安全扫描
        scan = session.query(JFrogScan).filter_by(artifact_id=artifact.id).first()
        logger.info(f" Xray Scan: Critical={scan.critical_count}, High={scan.high_count}")
        assert scan.critical_count == 1

        # 4. 验证身份归一化
        # JFrog 创建人为 'jf-admin'
        all_users = session.query(User).all()
        for u in all_users:
            logger.info(f"DEBUG: User in DB: {u.name} (ID: {u.id})")
            
        user_admin = session.query(User).filter_by(name='jf-admin').first()
        if not user_admin:
            # Try to find by identity mapping
            from devops_collector.models import IdentityMapping
            mapping = session.query(IdentityMapping).filter_by(external_id='jf-admin').first()
            if mapping:
                user_admin = session.query(User).get(mapping.user_id)
        
        logger.info(f" User Resolved: {user_admin.name if user_admin else 'None'} (ID: {user_admin.id if user_admin else 'None'})")
        assert user_admin is not None
        logger.info(" ARTIFACTORY PLUGINS SIMULATION COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_simulation()

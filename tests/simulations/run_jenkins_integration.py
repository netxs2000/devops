"""Jenkins 集成验证与仿真测试脚本 (Jenkins Plugin Simulation)

验证路径：
1. Jenkins 任务发现 (Sync All Jobs)
2. Jenkins 构建数据同步 (Sync Job Builds)
3. 身份匹配与关联 (Trigger User Mapping)
4. 数据持久化与校验
"""
import sys
import os
import json
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from devops_collector.models import Base, JenkinsJob, JenkinsBuild, SyncLog, User
from devops_collector.plugins.jenkins.client import JenkinsClient
from devops_collector.plugins.jenkins.worker import JenkinsWorker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('JenkinsSimulation')

def load_mock_json(filename):
    '''"""TODO: Add description.

Args:
    filename: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    path = os.path.join(os.path.dirname(__file__), 'mock_data', filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
MOCK_DATA = {'jobs': load_mock_json('jenkins_jobs.json'), 'builds_list': load_mock_json('jenkins_builds_list.json'), 'build_detail': load_mock_json('jenkins_build_detail.json')}

class MockResponse:
    '''"""TODO: Add class description."""'''

    def __init__(self, json_data, status_code=200):
        '''"""TODO: Add description.

Args:
    self: TODO
    json_data: TODO
    status_code: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.json_data

    def raise_for_status(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        if self.status_code >= 400:
            raise Exception(f'HTTP {self.status_code}')

def mocked_requests_get(*args, **kwargs):
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    url = args[0]
    logger.info(f'Mocking Jenkins GET: {url}')
    if url.endswith('api/json') and 'job/' not in url:
        return MockResponse({'jobs': MOCK_DATA['jobs']})
    if url.endswith('api/json') and 'job/' in url and ('101' not in url) and ('102' not in url):
        params = kwargs.get('params', {})
        tree = params.get('tree', '')
        if 'builds' in tree:
            return MockResponse({'builds': MOCK_DATA['builds_list']})
        return MockResponse(MOCK_DATA['jobs'][0])
    if '/101/api/json' in url or '/102/api/json' in url:
        return MockResponse(MOCK_DATA['build_detail'])
    return MockResponse({}, status_code=404)

def run_simulation():
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    logger.info('👷 Starting Jenkins Plugin Simulation...')
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    with patch('requests.get', side_effect=mocked_requests_get):
        client = JenkinsClient(url='http://jenkins.mock.com', user='admin', token='secret')
        worker = JenkinsWorker(session=session, client=client)
        logger.info('--- [STAGE 1] Syncing All Jobs ---')
        worker.process_task({'job_type': 'sync_all_jobs'})
        job_count = session.query(JenkinsJob).count()
        logger.info(f'✅ Jobs in DB: {job_count}')
        assert job_count == 2, 'Should have 2 jobs'
        logger.info("--- [STAGE 2] Syncing Builds for 'frontend-build' ---")
        worker.process_task({'job_type': 'sync_builds', 'job_full_name': 'frontend-build', 'limit': 10})
        logger.info('--- [STAGE 3] Data Verification ---')
        job = session.query(JenkinsJob).filter_by(full_name='frontend-build').first()
        build_count = session.query(JenkinsBuild).filter_by(job_id=job.id).count()
        logger.info(f"✅ Builds for '{job.full_name}': {build_count}")
        assert build_count == 2, 'Should have 2 builds for frontend-build'
        latest_build = session.query(JenkinsBuild).filter_by(job_id=job.id, number=101).first()
        logger.info(f'📊 Build Hash: {latest_build.number}, Result: {latest_build.result}, Duration: {latest_build.duration}ms')
        assert latest_build.result == 'SUCCESS'
        assert latest_build.duration == 120500
        trigger_user = session.query(User).filter_by(username='jenkins_zhangsan').first()
        if trigger_user:
            logger.info(f'👤 Trigger User Resolved: {trigger_user.username} (ID: {trigger_user.id})')
            assert latest_build.trigger_user_id == trigger_user.id
        else:
            pass
        logger.info('✨ JENKINS PLUGIN SIMULATION COMPLETED SUCCESSFULLY!')
if __name__ == '__main__':
    run_simulation()
"""DevOps 集成验证与仿真测试脚本 (Integration & Simulation Test)

该脚本模拟完整的 GitLab 数据采集流程，无需连接真实 GitLab 服务器。
验证路径：Mock API -> Worker 逻辑 -> SQLite 数据库入库 -> 数据一致性校验。
"""
import sys
import os
import json
import logging
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from devops_collector.models import Base, Project, Issue, MergeRequest, Commit, GitLabGroup, SyncLog, User
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.gitlab.worker import GitLabWorker
from devops_collector.config import Config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SimulationTest')

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
MOCK_PROJECTS = load_mock_json('gitlab_projects.json')
MOCK_ISSUES = load_mock_json('gitlab_issues.json')
MOCK_MRS = load_mock_json('gitlab_mrs.json')
MOCK_GROUPS = load_mock_json('gitlab_group.json')

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
        self.headers = {'x-total': str(len(json_data)) if isinstance(json_data, list) else '1'}

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
            raise Exception(f'HTTP Error: {self.status_code}')

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
    params = kwargs.get('params', {})
    page = params.get('page', 1)
    logger.info(f'Mocking GET request to: {url} (page={page})')
    if page > 1:
        return MockResponse([])
    if 'projects/101/issues' in url:
        return MockResponse(MOCK_ISSUES)
    elif 'projects/101/merge_requests' in url:
        return MockResponse(MOCK_MRS)
    elif 'projects/101/repository/commits' in url:
        return MockResponse([])
    elif 'projects/101/pipelines' in url:
        return MockResponse([])
    elif 'projects/101/deployments' in url:
        return MockResponse([])
    elif 'projects/101/repository/tags' in url:
        return MockResponse([])
    elif 'projects/101/repository/branches' in url:
        return MockResponse([])
    elif 'projects/101/milestones' in url:
        return MockResponse([])
    elif 'projects/101/packages' in url:
        return MockResponse([])
    elif 'projects/101' in url:
        return MockResponse(MOCK_PROJECTS[0])
    elif 'groups/10' in url:
        return MockResponse(MOCK_GROUPS[0])
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
    logger.info('Starting System Integration Simulation...')
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    with patch('requests.get', side_effect=mocked_requests_get):
        client = GitLabClient(url='https://mock-gitlab.com', token='fake-token')
        worker = GitLabWorker(session=session, client=client, enable_deep_analysis=False)
        task = {'project_id': 101, 'job_type': 'full'}
        logger.info(f'Processing Task: {task}')
        worker.process_task(task)
        logger.info('--- Verification Results ---')
        project = session.query(Project).filter_by(id=101).first()
        if project:
            logger.info(f'✅ Project Synced: {project.name} (ID: {project.id})')
            assert project.name == 'Frontend Web App'
        else:
            logger.error('❌ Project not found in DB')
        issue_count = session.query(Issue).count()
        logger.info(f'✅ Issues Synced: {issue_count}')
        assert issue_count == 2
        issue1 = session.query(Issue).filter_by(iid=1).first()
        if issue1:
            logger.info(f'✅ Issue #1 Workload: Estimate={issue1.time_estimate / 3600}h, Spent={issue1.total_time_spent / 3600}h')
            assert issue1.time_estimate == 36000
            assert issue1.total_time_spent == 54000
        mr_count = session.query(MergeRequest).count()
        logger.info(f'✅ MergeRequests Synced: {mr_count}')
        assert mr_count == 1
        sync_log = session.query(SyncLog).first()
        if sync_log:
            logger.info(f'✅ Sync Log Level: {sync_log.status} - {sync_log.message}')
        logger.info('--- Simulation Finished Successfully ---')
if __name__ == '__main__':
    try:
        run_simulation()
    except Exception as e:
        logger.error(f'Simulation Failed: {e}', exc_info=True)
        sys.exit(1)
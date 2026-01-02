"""Jira 插件集成验证与仿真测试脚本 (Jira Plugin Simulation)

验证路径：
1. Jira 用户与组织同步 (Groups & Users)
2. Jira 项目元数据同步 (Project)
3. 看板与 Sprint 同步 (Agile Entities)
4. Issue 及其变更历史同步 (Issues & Changelog)
5. 身份归一化验证
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
from devops_collector.models import Base, JiraProject, JiraBoard, JiraSprint, JiraIssue, JiraIssueHistory, User, Organization
from devops_collector.plugins.jira.client import JiraClient
from devops_collector.plugins.jira.worker import JiraWorker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('JiraSimulation')

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
MOCK_DATA = {'projects': load_mock_json('jira_projects.json'), 'boards': load_mock_json('jira_boards.json'), 'sprints': load_mock_json('jira_sprints.json'), 'issues': load_mock_json('jira_issues.json'), 'users': load_mock_json('jira_users.json'), 'groups': load_mock_json('jira_groups.json')}

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
    logger.info(f'Mocking Jira GET: {url}')
    if '/rest/api/3/groups/picker' in url:
        return MockResponse(MOCK_DATA['groups'])
    if '/rest/api/3/users/search' in url:
        return MockResponse(MOCK_DATA['users'])
    if '/rest/api/3/project/PROJ' in url:
        return MockResponse(MOCK_DATA['projects'][0])
    if '/rest/agile/1.0/board' in url and 'sprint' not in url:
        return MockResponse(MOCK_DATA['boards'])
    if '/rest/agile/1.0/board/1/sprint' in url:
        return MockResponse(MOCK_DATA['sprints'])
    if '/rest/api/3/search' in url:
        return MockResponse(MOCK_DATA['issues'])
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
    logger.info(' Jira Plugin Simulation Initializing...')
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    with patch('requests.get', side_effect=mocked_requests_get):
        client = JiraClient(url='https://mock-jira.atlassian.net', email='admin@example.com', api_token='token')
        worker = JiraWorker(session=session, client=client)
        logger.info("--- [STAGE 1] Syncing Jira Data for project 'PROJ' ---")
        worker.process_task({'project_key': 'PROJ'})
        logger.info('--- [STAGE 2] Data Verification ---')
        proj = session.query(JiraProject).filter_by(key='PROJ').first()
        logger.info(f' Project: {proj.name} (Lead: {proj.lead_name})')
        assert proj.name == 'E-Commerce Rebirth'
        dev_group = session.query(Organization).filter_by(name='Developers').first()
        logger.info(f' Group: {dev_group.name} (Level: {dev_group.level})')
        assert dev_group is not None
        user_lisi = session.query(User).filter_by(email='lisi@example.com').first()
        logger.info(f' User Resolved: {user_lisi.name} ({user_lisi.email})')
        assert user_lisi is not None
        board = session.query(JiraBoard).first()
        sprint_count = session.query(JiraSprint).count()
        logger.info(f' Board: {board.name}, Sprints synced: {sprint_count}')
        assert sprint_count == 2
        issue_count = session.query(JiraIssue).count()
        logger.info(f' Issues synced: {issue_count}')
        assert issue_count == 2
        issue1 = session.query(JiraIssue).filter_by(key='PROJ-1').first()
        history_count = session.query(JiraIssueHistory).filter_by(issue_id=issue1.id).count()
        logger.info(f' History for PROJ-1: {history_count} items')
        assert history_count == 1
        status_change = session.query(JiraIssueHistory).filter_by(issue_id=issue1.id, field='status').first()
        logger.info(f' Status Change: {status_change.from_string} -> {status_change.to_string}')
        assert status_change.to_string == 'In Progress'
        logger.info(' JIRA PLUGIN SIMULATION COMPLETED SUCCESSFULLY!')
if __name__ == '__main__':
    run_simulation()
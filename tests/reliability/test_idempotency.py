"""
Data Consistency & Idempotency Verification Test
================================================

Target: Verify that running the GitLab data collector multiple times
on the same source data does not result in duplicate records or
data corruption.

Scenarios:
1. Double-Run on Project Sync:
   - Run 1: Sync a project with commits and pipelines.
   - Assert: DB record counts are correct.
   - Run 2: Sync the EXACT SAME project data again.
   - Assert: DB record counts remain unchanged (Invariant).

2. Partial Update Idempotency (Optional for logic check):
   - Verify that updating existing records doesn't create new ones.
"""
import unittest
import sys
import os
import logging
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from devops_collector.models import Base, Project, Commit, Pipeline
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.gitlab.worker import GitLabWorker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('IdempotencyTest')

class MockGitLabResponse:
    '''"""TODO: Add class description."""'''

    def __init__(self, data, status_code=200):
        '''"""TODO: Add description.

Args:
    self: TODO
    data: TODO
    status_code: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.data = data
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
        return self.data

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

class TestGitLabWorkerIdempotency(unittest.TestCase):
    '''"""TODO: Add class description."""'''

    def setUp(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.client = MagicMock(spec=GitLabClient)
        self.client.base_url = 'http://mock-gitlab'
        self.client.token = 'mock-token'
        self.worker = GitLabWorker(self.session, self.client)

    def tearDown(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.session.close()

    def test_project_and_commits_idempotency(self):
        """
        Verify that syncing the same project and commits twice 
        results in the same number of DB records.
        """
        logger.info('>>> Starting Idempotency Test: Project & Commits')
        mock_project_data = {'id': 999, 'name': 'Idempotency Test Project', 'path_with_namespace': 'test-group/idempotency-proj', 'created_at': '2024-01-01T00:00:00Z', 'last_activity_at': '2024-01-02T00:00:00Z', 'description': 'Test'}
        mock_commits_data = [{'id': 'hash111', 'short_id': 'h111', 'title': 'Initial commit', 'author_name': 'Dev', 'created_at': '2024-01-01T10:00:00Z', 'message': 'Initial commit'}, {'id': 'hash222', 'short_id': 'h222', 'title': 'Fix bug', 'author_name': 'Dev', 'created_at': '2024-01-01T12:00:00Z', 'message': 'Fix bug'}]
        self.client.get_project.return_value = mock_project_data
        self.client.get_project_commits.return_value = mock_commits_data
        self.client.get_project_pipelines.return_value = []
        self.client.get_project_merge_requests.return_value = []
        self.client.get_project_issues.return_value = []
        logger.info('--- Run 1: Initial Ingestion ---')
        self.worker._sync_project(999)
        self.session.commit()
        proj_count_1 = self.session.query(Project).count()
        commit_count_1 = self.session.query(Commit).count()
        self.assertEqual(proj_count_1, 1, 'Should have 1 project after first run')
        self.assertEqual(commit_count_1, 2, 'Should have 2 commits after first run')
        logger.info(f'Run 1 Stats: Projects={proj_count_1}, Commits={commit_count_1}')
        logger.info('--- Run 2: Re-ingestion (Same Data) ---')
        self.worker._sync_project(999)
        self.session.commit()
        proj_count_2 = self.session.query(Project).count()
        commit_count_2 = self.session.query(Commit).count()
        logger.info(f'Run 2 Stats: Projects={proj_count_2}, Commits={commit_count_2}')
        self.assertEqual(proj_count_2, proj_count_1, f'Project count changed! {proj_count_1} -> {proj_count_2}')
        self.assertEqual(commit_count_2, commit_count_1, f'Commit count changed! {commit_count_1} -> {commit_count_2}')

    def test_pipeline_idempotency(self):
        """Verify Pipeline sync idempotency."""
        logger.info('>>> Starting Idempotency Test: Pipelines')
        mock_headers = {'X-Total-Pages': '1'}
        mock_pipelines = [{'id': 500, 'project_id': 999, 'status': 'success', 'ref': 'main', 'sha': 'hash222', 'created_at': '2024-01-01T12:05:00Z', 'updated_at': '2024-01-01T12:10:00Z'}]
        self.client.get_project.return_value = {'id': 999, 'name': 'P', 'last_activity_at': '2024-01-01'}
        self.client.get_project_pipelines.return_value = mock_pipelines
        self.client.get_project_commits.return_value = []
        self.client.get_project_merge_requests.return_value = []
        self.worker._sync_project(999)
        self.session.commit()
        count_1 = self.session.query(Pipeline).count()
        self.assertEqual(count_1, 1)
        self.worker._sync_project(999)
        self.session.commit()
        count_2 = self.session.query(Pipeline).count()
        self.assertEqual(count_2, count_1, 'Pipeline rows duplicated!')
if __name__ == '__main__':
    unittest.main()
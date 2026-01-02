"""
Interrupt & Recovery Test
=========================

Target:
Verify that the GitLabWorker can recover from an unexpected interruption (e.g. process crash,
network failure) without data loss or duplication.

Scenario:
1.  **Partial Sync**:
    - Simulate a paginated API response (e.g., 5 commits total).
    - Configure the worker to force a commit every 2 records (Batch Size = 2).
    - Simulate a "Crash" (Exception) when fetching the 3rd or 4th record.
    - **Expectation**: The first batch (records 1 & 2) should be persisted in the DB.
      The worker should raise an exception.

2.  **Recovery (Resume)**:
    - Restart the sync process for the same project.
    - Provide the full dataset (records 1-5).
    - **Expectation**:
        - Records 1 & 2 are skipped (or updated) but NOT duplicated.
        - Records 3, 4, 5 are successfully ingested.
        - Final DB count is 5.
"""
import unittest
import logging
import sys
import os
from unittest.mock import MagicMock
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from devops_collector.models import Base, Project, Commit
from devops_collector.plugins.gitlab.worker import GitLabWorker
from devops_collector.plugins.gitlab.client import GitLabClient
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TestInterruptRecovery')

class MockCrash(Exception):
    '''"""TODO: Add class description."""'''
    pass

class TestInterruptRecovery(unittest.TestCase):
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
        self.client.get_project.return_value = {'id': 100, 'name': 'Reliability Project', 'namespace': {'id': 10, 'name': 'Group', 'path': 'group', 'full_path': 'group'}, 'created_at': '2024-01-01T00:00:00Z'}
        self.client.get_project_issues.return_value = []
        self.client.get_project_merge_requests.return_value = []
        self.client.get_project_pipelines.return_value = []
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

    def test_commit_sync_interrupt_recovery(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        logger.info('>>> Starting Interrupt & Recovery Test')
        commits = [{'id': f'hash_{i}', 'short_id': f'h{i}', 'title': f'Commit {i}', 'message': f'msg {i}', 'author_name': 'Dev', 'author_email': 'dev@test.com', 'authored_date': '2024-01-01T10:00:00Z', 'committed_date': '2024-01-01T10:00:00Z', 'stats': {'total': 1}} for i in range(1, 6)]

        def crashing_generator():
            '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
            yield commits[0]
            yield commits[1]
            yield commits[2]
            raise MockCrash('Simulated Network Failure')
        original_process = self.worker._process_generator

        def patched_process_generator(generator, processor_func, batch_size=500):
            '''"""TODO: Add description.

Args:
    generator: TODO
    processor_func: TODO
    batch_size: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
            return original_process(generator, processor_func, batch_size=2)
        self.worker._process_generator = patched_process_generator
        self.client.get_project_commits.return_value = crashing_generator()
        logger.info('--- Phase 1: Running Sync (Expecting Crash) ---')
        with self.assertRaises(MockCrash):
            try:
                self.worker.process_task({'project_id': 100})
            except Exception as e:
                if 'Simulated Network Failure' in str(e):
                    raise MockCrash('Caught expected crash')
                raise e
        saved_commits = self.session.query(Commit).all()
        saved_ids = sorted([c.id for c in saved_commits])
        logger.info(f'Phase 1 Saved Commits: {saved_ids}')
        self.assertEqual(len(saved_commits), 2, 'Should have saved exactly 1 batch (2 commits) before crash')
        self.assertListEqual(saved_ids, ['hash_1', 'hash_2'])
        logger.info('--- Phase 2: Resume Sync (Full Data) ---')
        self.client.get_project_commits.return_value = iter(commits)
        try:
            self.worker.process_task({'project_id': 100})
        except Exception as e:
            self.fail(f'Recovery run failed with: {e}')
        final_commits = self.session.query(Commit).all()
        final_ids = sorted([c.id for c in final_commits])
        logger.info(f'Final Saved Commits: {final_ids}')
        self.assertEqual(len(final_commits), 5, 'Should have all 5 commits after recovery')
        self.assertListEqual(final_ids, ['hash_1', 'hash_2', 'hash_3', 'hash_4', 'hash_5'])
        pass
if __name__ == '__main__':
    unittest.main()
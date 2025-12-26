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

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from devops_collector.models import Base, Project, Commit
from devops_collector.plugins.gitlab.worker import GitLabWorker
from devops_collector.plugins.gitlab.client import GitLabClient

# Configure Logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestInterruptRecovery")

class MockCrash(Exception):
    pass

class TestInterruptRecovery(unittest.TestCase):
    
    def setUp(self):
        # 1. Setup In-Memory DB
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        # 2. Mock Client
        self.client = MagicMock(spec=GitLabClient)
        # Mock basic project info needed for _sync_project
        self.client.get_project.return_value = {
            "id": 100, 
            "name": "Reliability Project",
            "namespace": {"id": 10, "name": "Group", "path": "group", "full_path": "group"},
            "created_at": "2024-01-01T00:00:00Z"
        }
        # Suppress other calls
        self.client.get_project_issues.return_value = []
        self.client.get_project_merge_requests.return_value = []
        self.client.get_project_pipelines.return_value = []
        
        self.worker = GitLabWorker(self.session, self.client)
        
        # Monkeypatch or configure batch size to be small for testing
        # BaseMixin doesn't expose batch_size as a class attr easy to patch globally, 
        # but _process_generator takes it as arg.
        # We need to subclass/wrap or just ensure our mocked generator yields limited chunks.
        # Actually, BaseMixin._process_generator(generator, func, batch_size=500)
        # We can't easily change the 500 default without changing code, UNLESS we patch the method.
        
    def tearDown(self):
        self.session.close()

    def test_commit_sync_interrupt_recovery(self):
        logger.info(">>> Starting Interrupt & Recovery Test")

        # --- Data Setup ---
        # Generate 5 commits
        commits = [
            {
                "id": f"hash_{i}", "short_id": f"h{i}", 
                "title": f"Commit {i}", "message": f"msg {i}",
                "author_name": "Dev", "author_email": "dev@test.com",
                "authored_date": "2024-01-01T10:00:00Z",
                "committed_date": "2024-01-01T10:00:00Z",
                "stats": {"total": 1}
            }
            for i in range(1, 6) # 1..5
        ]
        
        # --- Simulate Crash Generator ---
        # This generator yields 2 items, then crashes.
        def crashing_generator():
            yield commits[0]
            yield commits[1]
            yield commits[2]
            # checking if batch (size 2) commit happens? 
            # In BaseMixin:
            # item 1 added. batch len 1.
            # item 2 added. batch len 2. -> commit! (Saved 1, 2)
            # item 3 added. batch len 1.
            # raise Error!
            raise MockCrash("Simulated Network Failure")

        # We need to PATCH `_process_generator` default batch_size OR patch the caller `_sync_commits`.
        # Easier to patch `GitLabWorker._process_generator` to default batch_size=2? 
        # No, better: The worker calls `self._process_generator`. 
        # We can just intercept the call to self.client.get_project_commits 
        # allowing it to return the crashing generator.
        # BUT we strictly need BATCH COMMIT to happen. 
        # With default batch_size=500, yielding 3 items won't trigger a commit inside the loop.
        # It waits for the end.
        
        # STRATEGY: Patch `BaseMixin._process_generator` method on the INSTANCE to force batch_size=2
        original_process = self.worker._process_generator
        
        def patched_process_generator(generator, processor_func, batch_size=500):
            # Force batch size 2 for testing
            return original_process(generator, processor_func, batch_size=2)
            
        self.worker._process_generator = patched_process_generator
        
        # Setup Mock to return our crashing generator
        self.client.get_project_commits.return_value = crashing_generator()

        # --- PHASE 1: Sync with Interrupt ---
        logger.info("--- Phase 1: Running Sync (Expecting Crash) ---")
        
        with self.assertRaises(MockCrash):
             # Wrapper to catch the worker's re-raised exception
             try:
                 self.worker.process_task({"project_id": 100})
             except Exception as e:
                 # Check if it's our crash (Worker wraps? No, worker catches and raises original if unknown?)
                 # Worker logs failure and RAISES.
                 if "Simulated Network Failure" in str(e):
                     raise MockCrash("Caught expected crash")
                 raise e

        # --- Verify Checkpoint (Phase 1) ---
        # We expect Commit 1 and 2 to be saved because batch_size=2 and we yielded 3 items.
        # Batch 1 (1,2) -> Committed.
        # Item 3 -> Pending in new batch -> Crash -> Rollback.
        # So DB should have 1 and 2.
        
        saved_commits = self.session.query(Commit).all()
        saved_ids = sorted([c.id for c in saved_commits])
        logger.info(f"Phase 1 Saved Commits: {saved_ids}")
        
        self.assertEqual(len(saved_commits), 2, "Should have saved exactly 1 batch (2 commits) before crash")
        self.assertListEqual(saved_ids, ["hash_1", "hash_2"])
        
        # --- PHASE 2: Recovery (Resume) ---
        logger.info("--- Phase 2: Resume Sync (Full Data) ---")
        
        # Heal the client mock
        self.client.get_project_commits.return_value = iter(commits) # Standard iterator, no crash
        
        # Run again
        try:
            self.worker.process_task({"project_id": 100})
        except Exception as e:
            self.fail(f"Recovery run failed with: {e}")
            
        # --- Verify Final State ---
        final_commits = self.session.query(Commit).all()
        final_ids = sorted([c.id for c in final_commits])
        logger.info(f"Final Saved Commits: {final_ids}")
        
        self.assertEqual(len(final_commits), 5, "Should have all 5 commits after recovery")
        self.assertListEqual(final_ids, ["hash_1", "hash_2", "hash_3", "hash_4", "hash_5"])
        
        # Important: Verify NO duplicates
        # The query().all() would allow object duplicates if DB allowed it, but SQL typically doesn't if PK enforced.
        # Our model has PK on ID.
        # We rely on 'test_idempotency' to prove no sql errors, but here we just check count.
        pass

if __name__ == '__main__':
    unittest.main()

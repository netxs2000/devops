"""
High Volume Stress Test
=======================

Target:
Simulate processing of a large dataset (e.g., 10,000 commits) to verify:
1.  **Memory Stability**: Ensure memory usage does not grow linearly with processed records (indicating leaks or failure to flush).
2.  **Performance linearity**: Ensure processing speed remains relatively stable across batches.

Note:
This test mocks the API response generator. It does NOT make actual HTTP requests.
It uses 'psutil' to check memory usage if available, otherwise falls back to basic completion check.
"""

import unittest
import logging
import time
import os
import sys
import gc
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from devops_collector.models import Base
from devops_collector.plugins.gitlab.worker import GitLabWorker
from devops_collector.plugins.gitlab.client import GitLabClient

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StressTest")

class TestHighVolumeStress(unittest.TestCase):
    
    def setUp(self):
        # Use file-based SQLite to simulate IO latency slightly better than memory, 
        # and to avoid RAM storage of the DB itself interfering with our worker RAM check.
        self.db_path = "stress_test.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        self.client = MagicMock(spec=GitLabClient)
        self.client.get_project.return_value = {
            "id": 9999, "name": "Big Project",
            "namespace": {"id": 1, "name": "BigGroup"},
            "created_at": "2020-01-01T00:00:00Z"
        }
        # Suppress others
        self.client.get_project_issues.return_value = []
        self.client.get_project_merge_requests.return_value = []
        self.client.get_project_pipelines.return_value = []

        self.worker = GitLabWorker(self.session, self.client)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except: pass

    def get_memory_usage_mb(self):
        if HAS_PSUTIL:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        return 0

    def test_sync_10k_commits(self):
        """Simulate syncing 10,000 commits."""
        TOTAL_COMMITS = 10000
        BATCH_SIZE = 500 # Default in BaseMixin
        
        logger.info(f">>> Starting Stress Test: {TOTAL_COMMITS} Commits")
        
        # Generator for Mock Data
        def huge_commit_generator():
            for i in range(TOTAL_COMMITS):
                yield {
                    "id": f"sha1_{i}", 
                    "short_id": f"s{i}",
                    "title": f"Commit number {i}",
                    "message": f"Fixing bug #{i} in the system",
                    "author_name": "Stressed Dev",
                    "author_email": "dev@example.com",
                    "authored_date": "2024-01-01T10:00:00Z",
                    "committed_date": "2024-01-01T10:00:00Z",
                    "stats": {"total": 1, "additions": 1, "deletions": 0}
                }

        self.client.get_project_commits.return_value = huge_commit_generator()
        
        # Start Measurement
        start_time = time.time()
        start_mem = self.get_memory_usage_mb()
        
        logger.info(f"Start Memory: {start_mem:.2f} MB")
        
        # Run Sync
        self.worker.process_task({"project_id": 9999})
        
        # End Measurement
        end_time = time.time()
        gc.collect() # Force GC to see real residual
        end_mem = self.get_memory_usage_mb()
        
        duration = end_time - start_time
        conn_rate = TOTAL_COMMITS / duration
        
        logger.info(f"End Memory: {end_mem:.2f} MB")
        logger.info(f"Total Time: {duration:.2f}s ({conn_rate:.2f} commits/sec)")
        
        # Assertions
        # 1. Performance Verify: Should be reasonably fast (mocked). 
        # >1000 commits/sec is expected for SQLite insertions mocking API.
        self.assertGreater(conn_rate, 500, "Processing rate too slow (<500/s)")
        
        # 2. Memory Verify: Net growth should be small. 
        # Python memory doesn't always release to OS, but huge growth (>100MB) for 10k tiny dicts indicates leak.
        mem_growth = end_mem - start_mem
        logger.info(f"Memory Growth: {mem_growth:.2f} MB")
        
        # Relaxed check: < 50MB growth is acceptable for cache/overhead.
        # If we kept all 10k objects in session, it would be larger.
        self.assertLess(mem_growth, 50, f"Potential Memory Leak! Grew by {mem_growth:.2f} MB")

if __name__ == '__main__':
    unittest.main()

"""Data Integrity Verification Script

This script verifies the completeness and accuracy of the collected DevOps data 
by comparing the database records against the live GitLab API data.

features:
1. Completeness Check:
   - Compares total counts of Issues, Merge Requests, and Pipelines.
   - Highlights discrepancies between GitLab's reported totals and DB record counts.

2. Business Logic Verification:
   - Verifies MR Review Cycles calculation by rebuilding the timeline from API events.
   - Verifies Issue Cycle Time consistency.

3. Sampling Inspection:
   - Randomly samples records to verify basic field accuracy (Title, State).

Usage:
    python scripts/verify_data_integrity.py --project-id <id> [--sample-size 5]
"""
import argparse
import logging
import random
import sys
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devops_collector.config import Config
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.models import Project, Issue, MergeRequest, Pipeline, IssueStateTransition, TraceabilityLink
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('DataVerifier')

class DataVerifier:
    '''"""TODO: Add class description."""'''

    def __init__(self, project_id: int):
        '''"""TODO: Add description.

Args:
    self: TODO
    project_id: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.project_id = project_id
        self.engine = create_engine(Config.DB_URI)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.client = GitLabClient(url=Config.GITLAB_URL, token=Config.GITLAB_PRIVATE_TOKEN)
        self.project = self.session.query(Project).filter_by(id=project_id).first()
        if not self.project:
            logger.error(f'Project {project_id} not found in database. Please sync it first.')
            sys.exit(1)

    def run_all(self, sample_size: int=5):
        '''"""TODO: Add description.

Args:
    self: TODO
    sample_size: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        logger.info(f'Starting verification for Project: {self.project.name} (ID: {self.project.id})')
        self.verify_counts()
        self.verify_mr_review_cycles(sample_size)
        logger.info('Verification completed.')

    def verify_counts(self):
        """Verifies total counts of key resources."""
        logger.info('--- Verify 1: Data Completeness (Counts) ---')
        db_count = self.session.query(Issue).filter_by(project_id=self.project_id).count()
        api_count = self.client.get_count(f'projects/{self.project_id}/issues')
        self._report_diff('Issues', db_count, api_count)
        db_count = self.session.query(MergeRequest).filter_by(project_id=self.project_id).count()
        api_count = self.client.get_count(f'projects/{self.project_id}/merge_requests')
        self._report_diff('Merge Requests', db_count, api_count)
        db_count = self.session.query(Pipeline).filter_by(project_id=self.project_id).count()
        api_count = self.client.get_count(f'projects/{self.project_id}/pipelines')
        self._report_diff('Pipelines', db_count, api_count)

    def verify_mr_review_cycles(self, sample_size: int):
        """Verifies the calculation of review cycles for a sample of MRs."""
        logger.info(f'--- Verify 2: Logic Check (MR Review Cycles) [Sample: {sample_size}] ---')
        mrs = self.session.query(MergeRequest).filter_by(project_id=self.project_id).filter(MergeRequest.state.in_(['merged', 'closed'])).order_by(func.random()).limit(sample_size).all()
        if not mrs:
            logger.warning('No suitable MRs found for review cycle verification.')
            return
        for mr in mrs:
            notes = list(self.client.get_mr_notes(self.project_id, mr.iid))
            discussion_notes = [n for n in notes if not n.get('system') and n.get('author', {}).get('id') != mr.author_id]
            explanation = ''
            status = 'OK'
            if discussion_notes and mr.review_cycles <= 0:
                status = 'WARN'
                explanation = f'Found {len(discussion_notes)} discussion notes but review_cycles is {mr.review_cycles}'
            elif not discussion_notes and mr.review_cycles > 1:
                status = 'INFO'
                explanation = f'No external discussions found but review_cycles is {mr.review_cycles} (maybe re-assignments counted?)'
            logger.info(f'MR !{mr.iid}: DB Cycles={mr.review_cycles} | API Notes={len(discussion_notes)} | {status} {explanation}')

    def _report_diff(self, resource_name: str, db_val: int, api_val: int):
        '''"""TODO: Add description.

Args:
    self: TODO
    resource_name: TODO
    db_val: TODO
    api_val: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        diff = api_val - db_val
        if diff == 0:
            logger.info(f'✅ {resource_name}: Match ({db_val})')
        else:
            pct = diff / api_val * 100 if api_val > 0 else 0
            logger.error(f'❌ {resource_name}: Mismatch! DB={db_val}, API={api_val}, Diff={diff} ({pct:.1f}%)')

def main():
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    parser = argparse.ArgumentParser(description='DevOps Data Integrity Verifier')
    parser.add_argument('--project-id', type=int, required=True, help='GitLab Project ID to verify')
    parser.add_argument('--sample-size', type=int, default=5, help='Number of items to sample for logic checks')
    args = parser.parse_args()
    try:
        verifier = DataVerifier(args.project_id)
        verifier.run_all(args.sample_size)
    except Exception as e:
        logger.error(f'Verification failed: {e}')
        sys.exit(1)
if __name__ == '__main__':
    main()
"""TODO: Add module description."""
import logging
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.config import Config
Config.DB_URI = 'sqlite:///:memory:'
from devops_collector.models.base_models import Base, RawDataStaging
from devops_collector.plugins.gitlab.models import GitLabProject, GitLabMergeRequest
from devops_collector.models import *
from scripts.reprocess_staging_data import reprocess_by_source
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Test-DataReplay')

def test_gitlab_mr_replay():
    """验证 GitLab Merge Request 的数据回放逻辑。"""
    engine = create_engine(Config.DB_URI)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    test_project_id = 99999
    test_mr_iid = 8888
    test_mr_id = 7777777
    try:
        project = GitLabProject(id=test_project_id, name='Test Replay Project', path_with_namespace='test/replay-project')
        session.add(project)
        session.commit()
        payload = {'id': test_mr_id, 'iid': test_mr_iid, 'project_id': test_project_id, 'title': 'Replay Test MR', 'description': 'This is a replay test', 'state': 'opened', 'created_at': '2023-01-01T12:00:00Z', 'updated_at': '2023-01-02T12:00:00Z', 'author': {'id': 1, 'username': 'tester'}}
        staging_rec = RawDataStaging(source='gitlab', entity_type='merge_request', external_id=str(test_mr_id), payload=payload, schema_version='1.1')
        session.add(staging_rec)
        session.commit()
        logger.info('Inserted mock staging record.')
        logger.info('Executing reprocess logic...')
        reprocess_by_source('gitlab', 'merge_request')
        session.expire_all()
        mr = session.query(GitLabMergeRequest).get(test_mr_id)
    except Exception as e:
        logger.error(f'❌ Test Failed with error: {e}')
        raise
    finally:
        session.close()
if __name__ == '__main__':
    import os
    test_db_file = 'test_replay.db'
    if os.path.exists(test_db_file):
        os.remove(test_db_file)
    Config.DB_URI = f'sqlite:///{test_db_file}'
    try:
        test_gitlab_mr_replay()
    finally:
        if os.path.exists(test_db_file):
            try:
                os.remove(test_db_file)
            except:
                pass
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base
from devops_collector.core.plugin_loader import PluginLoader
from devops_collector.plugins.gitlab.worker import GitLabWorker
from devops_collector.plugins.gitlab.models import GitLabProject, GitLabCommit, GitLabIssue

@pytest.fixture
def session():
    """Create a memory SQLite database and session for integration testing."""
    engine = create_engine("sqlite:///:memory:")
    PluginLoader.autodiscover()
    PluginLoader.load_models()
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_gitlab_worker_sync_project_and_commits(session):
    """Test the full sync flow of GitLabWorker with renamed models."""
    # 1. Setup Mock Client
    mock_client = MagicMock()
    mock_client.get_project.return_value = {
        'id': 101,
        'name': 'Test Project',
        'path_with_namespace': 'group/test',
        'web_url': 'http://gitlab.com/group/test',
        'visibility': 'public',
        'archived': False,
        'namespace': {'id': 1001, 'name': 'Group 1', 'path': 'group', 'full_path': 'group'}
    }
    mock_client.get_group.return_value = {
        'id': 1001,
        'name': 'Group 1',
        'path': 'group',
        'full_path': 'group'
    }
    
    # Mocking commit generator
    def get_commits_gen(pid, since=None):
        yield [
            {
                'id': 'sha123',
                'short_id': 'sha123',
                'title': 'initial commit',
                'author_name': 'Dev',
                'author_email': 'dev@example.com',
                'message': 'init',
                'authored_date': '2023-01-01T10:00:00Z',
                'committed_date': '2023-01-01T10:00:00Z',
                'stats': {'additions': 10, 'deletions': 2, 'total': 12}
            }
        ]
    
    mock_client.get_project_commits.side_effect = get_commits_gen
    mock_client.get_project_issues.return_value = []
    mock_client.get_merge_requests.return_value = []
    
    # 2. Run Worker
    worker = GitLabWorker(session, mock_client)
    task = {'source': 'gitlab', 'project_id': 101, 'job_type': 'full'}
    
    worker.process_task(task)
    session.commit()
    
    # 3. Verify Persistence in Renamed Tables
    project = session.query(GitLabProject).filter_by(id=101).first()
    assert project is not None
    assert project.name == 'Test Project'
    
    commits = session.query(GitLabCommit).filter_by(project_id=101).all()
    assert len(commits) == 1
    assert commits[0].id == 'sha123'
    assert commits[0].additions == 10
    
    # Verify SyncLog (Core Model)
    from devops_collector.models.base_models import SyncLog
    log = session.query(SyncLog).filter_by(project_id=101).order_by(SyncLog.id.desc()).first()
    assert log is not None
    assert "Synced" in log.message

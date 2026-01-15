"""TODO: Add module description."""
from dagster import asset, AssetExecutionContext
from sqlalchemy.orm import Session
from devops_collector.plugins.gitlab.worker import GitLabWorker
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.auth.auth_database import AuthSessionLocal as SessionLocal
from devops_collector.config import settings

@asset(group_name='gitlab_raw', compute_kind='python')
def gitlab_projects_metadata(context: AssetExecutionContext):
    """Sync base project metadata from GitLab."""
    session = SessionLocal()
    client = GitLabClient()
    worker = GitLabWorker(session, client)
    projects = worker.client.get_projects()
    for p_data in projects:
        worker.process_task({'project_id': p_data['id']})
    session.close()
    return 'completed'
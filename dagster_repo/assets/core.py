"""TODO: Add module description."""
from dagster import asset, AssetExecutionContext
from devops_collector.plugins.gitlab.worker import GitLabWorker
from devops_collector.plugins.jira.worker import JiraWorker
from devops_collector.plugins.sonar.worker import SonarQubeWorker
from dagster_repo.resources import DatabaseResource

@asset(group_name='raw_data', compute_kind='python')
def gitlab_raw_data(context: AssetExecutionContext, db: DatabaseResource):
    """Assets representing raw data collected from GitLab."""
    context.log.info('Starting GitLab data collection...')
    worker = GitLabWorker()
    worker.run()
    context.log.info('GitLab data collection complete.')
    return 'completed'

@asset(group_name='raw_data', compute_kind='python')
def jira_raw_data(context: AssetExecutionContext):
    """Assets representing raw data collected from Jira."""
    worker = JiraWorker()
    worker.run()
    return 'completed'

@asset(group_name='raw_data', compute_kind='python')
def sonar_raw_data(context: AssetExecutionContext):
    """Assets representing raw data collected from SonarQube."""
    worker = SonarQubeWorker()
    worker.run()
    return 'completed'
"""初始化与发现脚本

用于首次初始化数据库，从 GitLab 和 SonarQube 自动发现所有项目并存入数据库。
这样 Scheduler 才能开始调度同步任务。

运行方式:
    python scripts/init_discovery.py
"""
import sys
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
sys.path.append(os.getcwd())
from devops_collector.config import settings
from devops_collector.models import Base
from devops_collector.plugins.gitlab.models import GitLabProject as Project
from devops_collector.plugins.sonarqube.models import SonarProject
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.plugins.sonarqube.client import SonarQubeClient
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Discovery')

def discover_gitlab(session):
    """从 GitLab 发现所有项目。"""
    if not settings.gitlab.url or not settings.gitlab.private_token:
        logger.warning('GitLab config missing, skipping discovery.')
        return
    logger.info(f'Connecting to GitLab at {settings.gitlab.url}...')
    client = GitLabClient(settings.gitlab.url, settings.gitlab.private_token)
    if not client.test_connection():
        logger.error('Failed to connect to GitLab. Check URL and Token.')
        return
    logger.info('Fetching GitLab projects...')
    page = 1
    total_new = 0
    total_existing = 0
    while True:
        try:
            response = client._get('projects', params={'page': page, 'per_page': 100})
            projects_data = response.json()
        except Exception as e:
            logger.error(f'Error fetching GitLab projects page {page}: {e}')
            break
        if not projects_data:
            break
        for p_data in projects_data:
            pid = p_data['id']
            existing = session.query(Project).filter_by(id=pid).first()
            if not existing:
                new_proj = Project(id=pid, name=p_data.get('name'), path_with_namespace=p_data.get('path_with_namespace'), description=p_data.get('description'), sync_status='PENDING')
                session.add(new_proj)
                total_new += 1
            else:
                existing.name = p_data.get('name')
                existing.path_with_namespace = p_data.get('path_with_namespace')
                total_existing += 1
        session.commit()
        logger.info(f'Processed GitLab page {page}. New: {total_new}, Existing: {total_existing}')
        page += 1
    logger.info(f'GitLab discovery finished. Total New: {total_new}, Total Existing: {total_existing}')

def discover_sonarqube(session):
    """从 SonarQube 发现所有项目。"""
    if not settings.sonarqube.url or not settings.sonarqube.token:
        logger.warning('SonarQube config missing, skipping discovery.')
        return
    logger.info(f'Connecting to SonarQube at {settings.sonarqube.url}...')
    client = SonarQubeClient(settings.sonarqube.url, settings.sonarqube.token)
    if not client.test_connection():
        logger.error('Failed to connect to SonarQube. Check URL and Token.')
        return
    logger.info('Fetching SonarQube projects...')
    try:
        projects = client.get_all_projects()
    except Exception as e:
        logger.error(f'Failed to fetch SonarQube projects: {e}')
        return
    total_new = 0
    total_existing = 0
    for p_data in projects:
        key = p_data['key']
        existing = session.query(SonarProject).filter_by(key=key).first()
        if not existing:
            new_proj = SonarProject(key=key, name=p_data.get('name'), qualifier=p_data.get('qualifier'), sync_status='PENDING')
            session.add(new_proj)
            total_new += 1
        else:
            existing.name = p_data.get('name')
            total_existing += 1
    session.commit()
    logger.info(f'SonarQube discovery finished. Found {len(projects)} total. New: {total_new}, Existing: {total_existing}')

def main():
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    logger.info('Starting Discovery Service...')
    logger.info(f'DB_URI: {settings.database.uri}')
    engine = create_engine(settings.database.uri)
    Session = sessionmaker(bind=engine)
    session = Session()
    Base.metadata.create_all(engine)
    try:
        discover_gitlab(session)
        print('-' * 50)
        discover_sonarqube(session)
    except Exception as e:
        logger.error(f'Discovery process failed: {e}')
    finally:
        session.close()
if __name__ == '__main__':
    main()
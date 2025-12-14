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

# Ensure devops_collector is in path
sys.path.append(os.getcwd())

from devops_collector.config import Config
from devops_collector.models import Base, Project, SonarProject
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.sonarqube.client import SonarQubeClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Discovery')

def discover_gitlab(session):
    """从 GitLab 发现所有项目。"""
    if not Config.GITLAB_URL or not Config.GITLAB_PRIVATE_TOKEN:
        logger.warning("GitLab config missing, skipping discovery.")
        return

    logger.info(f"Connecting to GitLab at {Config.GITLAB_URL}...")
    client = GitLabClient(Config.GITLAB_URL, Config.GITLAB_PRIVATE_TOKEN)
    
    if not client.test_connection():
        logger.error("Failed to connect to GitLab. Check URL and Token.")
        return

    logger.info("Fetching GitLab projects...")
    
    # 手动分页获取所有项目
    page = 1
    total_new = 0
    total_existing = 0
    
    while True:
        try:
            # 获取用户可访问的所有项目
            # 使用 membership=true 可只获取我是成员的项目，这里获取所有可见项目
            response = client._get('projects', params={'page': page, 'per_page': 100})
            projects_data = response.json()
        except Exception as e:
            logger.error(f"Error fetching GitLab projects page {page}: {e}")
            break
            
        if not projects_data:
            break
            
        for p_data in projects_data:
            pid = p_data['id']
            existing = session.query(Project).filter_by(id=pid).first()
            
            if not existing:
                new_proj = Project(
                    id=pid,
                    name=p_data.get('name'),
                    path_with_namespace=p_data.get('path_with_namespace'),
                    description=p_data.get('description'),
                    # 初始化为 PENDING 状态，等待 Scheduler 调度
                    sync_status='PENDING'
                )
                session.add(new_proj)
                total_new += 1
            else:
                # 更新基本信息
                existing.name = p_data.get('name')
                existing.path_with_namespace = p_data.get('path_with_namespace')
                total_existing += 1
                
        session.commit()
        logger.info(f"Processed GitLab page {page}. New: {total_new}, Existing: {total_existing}")
        page += 1

    logger.info(f"GitLab discovery finished. Total New: {total_new}, Total Existing: {total_existing}")

def discover_sonarqube(session):
    """从 SonarQube 发现所有项目。"""
    if not Config.SONARQUBE_URL or not Config.SONARQUBE_TOKEN:
         logger.warning("SonarQube config missing, skipping discovery.")
         return

    logger.info(f"Connecting to SonarQube at {Config.SONARQUBE_URL}...")
    client = SonarQubeClient(Config.SONARQUBE_URL, Config.SONARQUBE_TOKEN)
    
    if not client.test_connection():
        logger.error("Failed to connect to SonarQube. Check URL and Token.")
        return

    logger.info("Fetching SonarQube projects...")
    try:
        projects = client.get_all_projects()
    except Exception as e:
        logger.error(f"Failed to fetch SonarQube projects: {e}")
        return
        
    total_new = 0
    total_existing = 0
    
    for p_data in projects:
        key = p_data['key']
        existing = session.query(SonarProject).filter_by(key=key).first()
        
        if not existing:
            new_proj = SonarProject(
                key=key,
                name=p_data.get('name'),
                qualifier=p_data.get('qualifier'),
                sync_status='PENDING'
            )
            session.add(new_proj)
            total_new += 1
        else:
            existing.name = p_data.get('name')
            total_existing += 1
    
    session.commit()
    logger.info(f"SonarQube discovery finished. Found {len(projects)} total. New: {total_new}, Existing: {total_existing}")

def main():
    logger.info("Starting Discovery Service...")
    
    # 打印配置信息 (脱敏)
    logger.info(f"DB_URI: {Config.DB_URI}")
    
    engine = create_engine(Config.DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 确保表结构存在
    Base.metadata.create_all(engine)
    
    try:
        discover_gitlab(session)
        print("-" * 50)
        discover_sonarqube(session)
    except Exception as e:
        logger.error(f"Discovery process failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()

"""DevOps Collector 调度器模块

定时扫描数据库中的项目，将需要同步的项目发布到 RabbitMQ 任务队列。
"""
import time
import logging
import subprocess
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import Config
from .models.base_models import Base
from .mq import MessageQueue
from .core.plugin_loader import PluginLoader

logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger('Scheduler')

def main() -> None:
    """调度器主循环。"""
    # 动态加载所有插件模型
    PluginLoader.load_models()
    
    # 获取具体的模型类
    from devops_collector.plugins.gitlab.models import GitLabProject
    from devops_collector.plugins.sonarqube.models import SonarProject

    engine = create_engine(Config.DB_URI)
    Session = sessionmaker(bind=engine)
    mq = MessageQueue()
    Base.metadata.create_all(engine)
    logger.info('Scheduler started.')

    while True:
        session = Session()
        try:
            # 1. 扫描 GitLab 项目
            projects = session.query(GitLabProject).all()
            for proj in projects:
                should_sync = False
                if not proj.last_synced_at:
                    should_sync = True
                elif datetime.now(timezone.utc) - proj.last_synced_at.replace(tzinfo=timezone.utc) > timedelta(minutes=Config.SYNC_INTERVAL_MINUTES):
                    should_sync = True
                
                if should_sync and proj.sync_status != 'SYNCING':
                    task = {
                        'source': 'gitlab', 
                        'project_id': proj.id, 
                        'job_type': 'incremental' if proj.last_synced_at else 'full'
                    }
                    mq.publish_task(task)
                    proj.sync_status = 'QUEUED'
                    session.commit()

            # 2. 扫描 SonarQube 项目
            sonar_projects = session.query(SonarProject).all()
            for sp in sonar_projects:
                should_sync = False
                if not sp.last_synced_at:
                    should_sync = True
                elif datetime.now(timezone.utc) - sp.last_synced_at.replace(tzinfo=timezone.utc) > timedelta(hours=Config.SONARQUBE_SYNC_INTERVAL_HOURS):
                    should_sync = True
                
                if should_sync and sp.sync_status != 'SYNCING':
                    task = {
                        'source': 'sonarqube', 
                        'project_key': sp.key, 
                        'job_type': 'full', 
                        'sync_issues': Config.SONARQUBE_SYNC_ISSUES
                    }
                    mq.publish_task(task)
                    sp.sync_status = 'QUEUED'
                    session.commit()

            # 3. 执行 dbt 转换与反向 ETL
            try:
                logger.info('Triggering dbt run...')
                result = subprocess.run(
                    ['dbt', 'run', '--project-dir', 'dbt_project', '--profiles-dir', 'dbt_project'], 
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    logger.info('dbt run success')
                    from .core.reverse_etl import (
                        sync_talent_tags_to_mdm, 
                        sync_aligned_entities_to_mdm, 
                        sync_shadow_it_findings
                    )
                    sync_talent_tags_to_mdm(session)
                    sync_aligned_entities_to_mdm(session)
                    sync_shadow_it_findings(session)
                else:
                    logger.error(f'dbt run failed: {result.stderr}')
            except Exception as e:
                logger.error(f'Failed to run dbt or reverse ETL: {e}')

        except Exception as e:
            logger.error(f'Scheduler loop error: {e}')
            session.rollback()
        finally:
            session.close()
        
        time.sleep(60)

if __name__ == '__main__':
    main()
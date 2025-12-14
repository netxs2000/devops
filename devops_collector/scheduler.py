"""GitLab 数据采集调度器模块

定时扫描数据库中的项目，将需要同步的项目发布到 RabbitMQ 任务队列。
根据配置的同步间隔 (SYNC_INTERVAL_MINUTES) 决定是否触发同步。

运行方式:
    python -m gitlab_collector.scheduler
"""
import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone

from .config import Config
from .models import Base, Project, SonarProject
from .mq import MessageQueue

logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger('Scheduler')

def main() -> None:
    """调度器主循环函数。
    
    每分钟扫描一次数据库，检查哪些项目需要同步：
    1. GitLab 项目:
       - 从未同步过的项目 -> 触发全量同步
       - 超过同步间隔 -> 触发增量同步
    2. SonarQube 项目:
       - 从未同步过的项目 -> 触发全量同步
       - 超过同步间隔 -> 触发增量同步
    
    同步任务发布到 RabbitMQ，由 Worker 消费处理。
    """
    engine = create_engine(Config.DB_URI)
    Session = sessionmaker(bind=engine)
    mq = MessageQueue()
    
    # Ensure tables exist (for simplicity in this demo)
    Base.metadata.create_all(engine)
    
    logger.info("Scheduler started.")
    
    while True:
        session = Session()
        try:
            # === 1. GitLab Projects ===
            projects = session.query(Project).all()
            
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

            # === 2. SonarQube Projects ===
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

            
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
            session.rollback()
        finally:
            session.close()
        
        time.sleep(60) # Run every minute check

if __name__ == "__main__":
    main()

"""DevOps 数据采集资产。

负责执行各插件的 Worker 同步任务，并由 Dagster 管理其依赖与调度。
"""
from dagster import asset, AssetExecutionContext, Config
from devops_collector.plugins.gitlab.worker import GitLabWorker
from devops_collector.plugins.sonarqube.worker import SonarQubeWorker
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.sonarqube.client import SonarQubeClient
from devops_collector.plugins.gitlab.models import Project as GitLabProject
from devops_collector.plugins.sonarqube.models import SonarProject
from dagster_repo.resources import DatabaseResource
from devops_collector.config import settings

class SyncConfig(Config):
    """同步配置。"""
    project_ids: list[int] = []
    project_keys: list[str] = []

@asset(group_name='raw_data', compute_kind='python')
def gitlab_assets(context: AssetExecutionContext, db: DatabaseResource, config: SyncConfig):
    """从 GitLab 同步原始数据。"""
    engine = db.get_engine()
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    
    # 实例化客户端 (从配置获取)
    client = GitLabClient(
        url=settings.gitlab.url, 
        token=settings.gitlab.token
    )
    
    with Session() as session:
        worker = GitLabWorker(session, client)
        
        # 如果未指定 ID，则同步所有已知项目
        ids = config.project_ids or [p.id for p in session.query(GitLabProject).all()]
        
        for pid in ids:
            context.log.info(f"Syncing GitLab project: {pid}")
            worker.run_sync({"source": "gitlab", "project_id": pid}, 
                           model_cls=GitLabProject, pk_value=pid)
            
    return 'completed'

@asset(group_name='raw_data', compute_kind='python')
def sonarqube_assets(context: AssetExecutionContext, db: DatabaseResource, config: SyncConfig):
    """从 SonarQube 同步质量数据。"""
    engine = db.get_engine()
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    
    client = SonarQubeClient(
        url=settings.sonarqube.url, 
        token=settings.sonarqube.token
    )
    
    with Session() as session:
        worker = SonarQubeWorker(session, client)
        
        keys = config.project_keys or [p.key for p in session.query(SonarProject).all()]
        
        for key in keys:
            context.log.info(f"Syncing SonarQube project: {key}")
            worker.run_sync({"source": "sonarqube", "project_key": key}, 
                           model_cls=SonarProject, pk_field='key', pk_value=key)
            
    return 'completed'
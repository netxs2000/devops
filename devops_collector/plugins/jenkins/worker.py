"""Jenkins 数据采集 Worker

基于 BaseWorker 实现的 Jenkins 数据同步逻辑。
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from .client import JenkinsClient
from .models import JenkinsJob, JenkinsBuild
from devops_collector.core.identity_manager import IdentityManager

# 尝试导入 GitLab Project 用于映射
try:
    from devops_collector.plugins.gitlab.models import Project as GitLabProject
except ImportError:
    GitLabProject = None

logger = logging.getLogger(__name__)


class JenkinsWorker(BaseWorker):
    """Jenkins 数据采集 Worker。
    
    支持同步 Jenkins Job 基本信息和 Build 详细记录。
    
    同步策略:
    - 系统级别: 同步所有 Job 列表
    - Job 级别: 同步特定 Job 的所有或增量 Build 记录
    """
    
    def __init__(self, session: Session, client: JenkinsClient) -> None:
        """初始化 Jenkins Worker。
        
        Args:
            session: SQLAlchemy 数据库会话。
            client: Jenkins API 客户端。
        """
        super().__init__(session, client)

    def process_task(self, task: dict) -> None:
        """处理 Jenkins 同步任务。
        
        Args:
            task: {
                "source": "jenkins",
                "job_type": "sync_all_jobs" | "sync_builds",
                "job_full_name": str,  # 当 job_type 为 sync_builds 时必填
                "limit": int           # 构建同步数量限制
            }
        """
        job_type = task.get('job_type', 'sync_all_jobs')
        
        if job_type == 'sync_all_jobs':
            self.sync_all_jobs()
        elif job_type == 'sync_builds':
            job_full_name = task.get('job_full_name')
            if not job_full_name:
                raise ValueError("job_full_name is required for sync_builds task")
            limit = task.get('limit', 100)
            self.sync_job_builds(job_full_name, limit)
        else:
            logger.warning(f"Unknown job_type: {job_type}")

    def sync_all_jobs(self) -> int:
        """同步所有 Jenkins Job 信息。"""
        logger.info("Syncing all Jenkins jobs...")
        jobs_data = self.client.get_jobs()
        count = 0
        
        for j_data in jobs_data:
            full_name = j_data.get('fullName') or j_data.get('name')
            job = self.session.query(JenkinsJob).filter_by(full_name=full_name).first()
            
            if not job:
                job = JenkinsJob(full_name=full_name)
                self.session.add(job)
            
            job.name = j_data.get('name')
            job.url = j_data.get('url')
            job.description = j_data.get('description')
            job.color = j_data.get('color')
            job.raw_data = j_data
            job.last_synced_at = datetime.now(timezone.utc)
            job.sync_status = 'SUCCESS'
            
            # 尝试映射到 GitLab 项目 (简单匹配 strategy)
            if GitLabProject and not job.gitlab_project_id:
                # 假设 Job 名称或 FullName 包含 GitLab 项目路径
                # 这里可以根据实际情况调整匹配逻辑
                pass
            
            count += 1
            if count % 50 == 0:
                self.session.commit()
                
        self.session.commit()
        self.log_success(f"Synced {count} Jenkins jobs")
        return count

    def sync_job_builds(self, job_full_name: str, limit: int = 100) -> int:
        """同步特定 Job 的构建记录。"""
        logger.info(f"Syncing builds for job: {job_full_name} (limit={limit})")
        
        # 1. 确保 Job 在数据库中存在
        job = self.session.query(JenkinsJob).filter_by(full_name=job_full_name).first()
        if not job:
            # 如果不存在，尝试获取详情并创建
            j_data = self.client.get_job_details(job_full_name)
            job = JenkinsJob(
                full_name=job_full_name,
                name=j_data.get('name'),
                url=j_data.get('url')
            )
            self.session.add(job)
            self.session.flush()
            
        # 2. 获取构建列表
        builds_list = self.client.get_builds(job_full_name, limit)
        count = 0
        
        for b_summary in builds_list:
            build_num = b_summary['number']
            
            # 检查是否已存在且已完成
            existing_build = self.session.query(JenkinsBuild).filter_by(
                job_id=job.id, number=build_num
            ).first()
            
            if existing_build and not existing_build.building and existing_build.result:
                # 已同步且已完成，跳过 (增量同步逻辑)
                continue
                
            # 3. 获取构建详情
            try:
                b_data = self.client.get_build_details(b_summary['url'])
                
                if not existing_build:
                    existing_build = JenkinsBuild(job_id=job.id, number=build_num)
                    self.session.add(existing_build)
                
                existing_build.queue_id = b_data.get('queueId')
                existing_build.url = b_data.get('url')
                existing_build.result = b_data.get('result')
                existing_build.duration = b_data.get('duration')
                existing_build.building = b_data.get('building', False)
                existing_build.executor = b_data.get('executor')
                
                # 解析构建开始时间
                if b_data.get('timestamp'):
                    existing_build.timestamp = datetime.fromtimestamp(
                        b_data['timestamp'] / 1000.0, tz=timezone.utc
                    )
                
                # 解析触发者
                actions = b_data.get('actions', [])
                for action in actions:
                    if action.get('_class') == 'hudson.model.CauseAction':
                        causes = action.get('causes', [])
                        if causes:
                            existing_build.trigger_type = causes[0].get('_class')
                            existing_build.trigger_user = causes[0].get('userName')
                            if existing_build.trigger_user:
                                u = IdentityManager.get_or_create_user(
                                    self.session, 'jenkins', 
                                    existing_build.trigger_user, # Jenkins ID usually matches username
                                    name=existing_build.trigger_user
                                )
                                existing_build.trigger_user_id = u.id
                
                existing_build.raw_data = b_data
                count += 1
                
                if count % 20 == 0:
                    self.session.commit()
                    
            except Exception as e:
                logger.error(f"Failed to sync build {build_num} for job {job_full_name}: {e}")
                
        self.session.commit()
        self.log_success(f"Synced {count} builds for job {job_full_name}")
        return count


# 注册插件
PluginRegistry.register_worker('jenkins', JenkinsWorker)

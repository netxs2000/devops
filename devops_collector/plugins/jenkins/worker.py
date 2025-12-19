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
from .parser import ReportParser
from devops_collector.models import (
    User, Organization, SyncLog, TestExecutionSummary
)
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
                # 策略 1: 完全匹配 path_with_namespace
                gitlab_project = self.session.query(GitLabProject).filter(
                    (GitLabProject.path_with_namespace == full_name) | 
                    (GitLabProject.name == job.name)
                ).first()
                
                if gitlab_project:
                    job.gitlab_project_id = gitlab_project.id
                    logger.info(f"Mapped Jenkins Job {full_name} to GitLab project {gitlab_project.id}")
            
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
                                # Jenkins 用户名通常即为 ID，我们将其作为 external_id 和 username 同时传入
                                u = IdentityManager.get_or_create_user(
                                    self.session, 'jenkins', 
                                    existing_build.trigger_user,
                                    name=existing_build.trigger_user,
                                    username=existing_build.trigger_user
                                )
                                existing_build.trigger_user_id = u.id
                
                existing_build.raw_data = b_data
                
                # 4. 尝试同步测试报告 (如果是已完成的构建)
                if not existing_build.building and existing_build.result:
                    self._sync_test_report(job, existing_build)

                count += 1
                
                if count % 20 == 0:
                    self.session.commit()
                    
            except Exception as e:
                logger.error(f"Failed to sync build {build_num} for job {job_full_name}: {e}")
                
        self.session.commit()
        self.log_success(f"Synced {count} builds for job {job_full_name}")
        return count

    def _sync_test_report(self, job: JenkinsJob, build: JenkinsBuild) -> None:
        """从 Jenkins 获取并同步测试报告。"""
        try:
            report_data = self.client.get_test_report(build.url)
            if not report_data:
                return

            summary = ReportParser.parse_jenkins_test_report(
                project_id=job.gitlab_project_id,
                build_id=str(build.number),
                report_data=report_data,
                job_name=job.name or ""
            )

            if summary:
                # 检查是否已存在 (幂等)
                existing = self.session.query(TestExecutionSummary).filter_by(
                    project_id=job.gitlab_project_id,
                    build_id=str(build.number),
                    test_level=summary.test_level
                ).first()

                if not existing:
                    self.session.add(summary)
                    logger.info(f"Saved test summary for build {build.number} ({summary.test_level})")
                else:
                    # 更新已有记录
                    existing.total_cases = summary.total_cases
                    existing.passed_count = summary.passed_count
                    existing.failed_count = summary.failed_count
                    existing.pass_rate = summary.pass_rate
                    existing.duration_ms = summary.duration_ms
                    existing.raw_data = summary.raw_data

        except Exception as e:
            logger.warning(f"Failed to sync test report for build {build.number}: {e}")


# 注册插件
PluginRegistry.register_worker('jenkins', JenkinsWorker)

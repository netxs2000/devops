"""Jenkins 数据采集 Worker

基于 BaseWorker 实现的 Jenkins 数据同步逻辑。
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
# from .client import JenkinsClient
from .models import JenkinsJob, JenkinsBuild
from .parser import ReportParser
from devops_collector.models import User, Organization, SyncLog, TestExecutionSummary
from devops_collector.core.identity_manager import IdentityManager
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
    SCHEMA_VERSION = '1.0'

    def __init__(self, session: Session, client: Any) -> None:
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
                raise ValueError('job_full_name is required for sync_builds task')
            limit = task.get('limit', 100)
            self.sync_job_builds(job_full_name, limit)
        else:
            logger.warning(f'Unknown job_type: {job_type}')

    def sync_all_jobs(self) -> int:
        """同步所有 Jenkins Job 信息。"""
        logger.info('Syncing all Jenkins jobs...')
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
            self.save_to_staging(source='jenkins', entity_type='job', external_id=full_name, payload=j_data, schema_version=self.SCHEMA_VERSION)
            job.raw_data = j_data
            job.last_synced_at = datetime.now(timezone.utc)
            job.sync_status = 'SUCCESS'
            if GitLabProject and (not job.gitlab_project_id):
                gitlab_project = self.session.query(GitLabProject).filter((GitLabProject.path_with_namespace == full_name) | (GitLabProject.name == job.name)).first()
                if gitlab_project:
                    job.gitlab_project_id = gitlab_project.id
                    logger.info(f'Mapped Jenkins Job {full_name} to GitLab project {gitlab_project.id}')
            count += 1
            if count % 50 == 0:
                self.session.commit()
        self.session.commit()
        self.log_success(f'Synced {count} Jenkins jobs')
        return count

    def sync_job_builds(self, job_full_name: str, limit: int=100) -> int:
        """同步特定 Job 的构建记录。"""
        logger.info(f'Syncing builds for job: {job_full_name} (limit={limit})')
        job = self.session.query(JenkinsJob).filter_by(full_name=job_full_name).first()
        if not job:
            j_data = self.client.get_job_details(job_full_name)
            job = JenkinsJob(full_name=job_full_name, name=j_data.get('name'), url=j_data.get('url'))
            self.session.add(job)
            self.session.flush()
        builds_list = self.client.get_builds(job_full_name, limit)
        count = 0
        for b_summary in builds_list:
            build_num = b_summary['number']
            existing_build = self.session.query(JenkinsBuild).filter_by(job_id=job.id, number=build_num).first()
            if existing_build and (not existing_build.building) and existing_build.result:
                continue
            try:
                b_data = self.client.get_build_details(b_summary['url'])
                self.save_to_staging(source='jenkins', entity_type='build', external_id=f'{job_full_name}#{build_num}', payload=b_data, schema_version=self.SCHEMA_VERSION)
                self._transform_build(job, existing_build, b_data)
                count += 1
                if count % 20 == 0:
                    self.session.commit()
            except Exception as e:
                logger.error(f'Failed to sync build {build_num} for job {job_full_name}: {e}')
        self.session.commit()
        self.log_success(f'Synced {count} builds for job {job_full_name}')
        return count

    def _transform_build(self, job: JenkinsJob, build: Optional[JenkinsBuild], b_data: dict) -> JenkinsBuild:
        """核心解析逻辑：将原始 Jenkins Build JSON 转换为 JenkinsBuild 模型。"""
        build_num = b_data['number']
        if not build:
            build = self.session.query(JenkinsBuild).filter_by(job_id=job.id, number=build_num).first()
        if not build:
            build = JenkinsBuild(job_id=job.id, number=build_num)
            self.session.add(build)
        build.queue_id = b_data.get('queueId')
        build.url = b_data.get('url')
        build.result = b_data.get('result')
        build.duration = b_data.get('duration')
        build.building = b_data.get('building', False)
        build.executor = b_data.get('executor')
        if b_data.get('timestamp'):
            build.timestamp = datetime.fromtimestamp(b_data['timestamp'] / 1000.0, tz=timezone.utc)
        actions = b_data.get('actions', [])
        for action in actions:
            if action.get('_class') == 'hudson.model.CauseAction':
                causes = action.get('causes', [])
                if causes:
                    build.trigger_type = causes[0].get('_class')
                    build.trigger_user = causes[0].get('userName')
                    if build.trigger_user:
                        u = IdentityManager.get_or_create_user(self.session, 'jenkins', build.trigger_user, name=build.trigger_user)
                        build.trigger_user_id = u.global_user_id
        build.raw_data = b_data
        if not build.building and build.result:
            self._sync_test_report(job, build)
        return build

    def _sync_test_report(self, job: JenkinsJob, build: JenkinsBuild) -> None:
        """从 Jenkins 获取并同步测试报告。"""
        try:
            report_data = self.client.get_test_report(build.url)
            if not report_data:
                return
            summary = ReportParser.parse_jenkins_test_report(project_id=job.gitlab_project_id, build_id=str(build.number), report_data=report_data, job_name=job.name or '')
            if summary:
                existing = self.session.query(TestExecutionSummary).filter_by(project_id=job.gitlab_project_id, build_id=str(build.number), test_level=summary.test_level).first()
                if not existing:
                    self.session.add(summary)
                    logger.info(f'Saved test summary for build {build.number} ({summary.test_level})')
                else:
                    existing.total_cases = summary.total_cases
                    existing.passed_count = summary.passed_count
                    existing.failed_count = summary.failed_count
                    existing.pass_rate = summary.pass_rate
                    existing.duration_ms = summary.duration_ms
                    existing.raw_data = summary.raw_data
        except Exception as e:
            logger.warning(f'Failed to sync test report for build {build.number}: {e}')

"""Plugin Core Service.

封装 CI/CD 及各类制品的查询逻辑。
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from devops_collector.core import security
from devops_collector.models.base_models import User


class PluginService:
    """处理跨平台的插件数据查询逻辑，确保 Router 保持纯粹。"""

    def __init__(self, session: Session):
        self.session = session

    def list_jenkins_jobs(self, current_user: User):
        """获取 Jenkins 任务列表（支持组织隔离）。"""
        from devops_collector.plugins.jenkins.models import JenkinsJob

        query = self.session.query(JenkinsJob)
        query = security.apply_plugin_privacy_filter(self.session, query, JenkinsJob, current_user)
        return query.all()

    def list_jenkins_builds(self, current_user: User, job_id: int):
        """获取特定任务的构建历史（含权限校验）。"""
        from devops_collector.plugins.jenkins.models import JenkinsBuild, JenkinsJob

        job = self.session.query(JenkinsJob).filter(JenkinsJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # 权限校验
        job_query = self.session.query(JenkinsJob).filter(JenkinsJob.id == job_id)
        job_query = security.apply_plugin_privacy_filter(self.session, job_query, JenkinsJob, current_user)
        if not job_query.first():
            raise HTTPException(status_code=403, detail="Access Denied to this Jenkins Job Data")

        return self.session.query(JenkinsBuild).filter(JenkinsBuild.job_id == job_id).order_by(JenkinsBuild.number.desc()).limit(100).all()

    def list_jfrog_artifacts(self, current_user: User):
        """获取 JFrog 制品列表（支持组织隔离）。"""
        from devops_collector.plugins.jfrog.models import JFrogArtifact

        query = self.session.query(JFrogArtifact)
        query = security.apply_plugin_privacy_filter(self.session, query, JFrogArtifact, current_user)
        return query.all()

    def list_nexus_components(self, current_user: User):
        """获取 Nexus 组件列表（支持组织隔离）。"""
        from devops_collector.plugins.nexus.models import NexusComponent

        query = self.session.query(NexusComponent)
        query = security.apply_plugin_privacy_filter(self.session, query, NexusComponent, current_user)
        return query.all()

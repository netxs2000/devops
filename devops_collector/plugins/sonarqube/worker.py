"""SonarQube 数据采集 Worker"""
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from devops_collector.core.utils import parse_iso8601
from .client import SonarQubeClient
from .models import SonarProject
from .transformer import SonarDataTransformer

try:
    from devops_collector.plugins.gitlab.models import Project as GitLabProject
except ImportError:
    GitLabProject = None

logger = logging.getLogger(__name__)

class SonarQubeWorker(BaseWorker):
    """SonarQube 数据采集 Worker。"""
    SCHEMA_VERSION = '1.0'

    def __init__(self, session: Session, client: SonarQubeClient, sync_issues: bool=False) -> None:
        super().__init__(session, client)
        self.sync_issues = sync_issues
        self.transformer = SonarDataTransformer(session)

    def process_task(self, task: dict) -> dict:
        """核心同步逻辑。"""
        project_key = task.get('project_key')
        if not project_key:
            raise ValueError("project_key is required")

        project = self._sync_project_metadata(project_key)
        if not project:
            raise ValueError(f'SonarQube project {project_key} not found')

        # 同步指标
        measure = self._sync_measures(project)
        
        # 同步问题 (可选)
        issues_count = 0
        if task.get('sync_issues', self.sync_issues):
            issues_count = self._sync_issues(project)
            
        return {
            "project": project.name,
            "coverage": measure.coverage if measure else None,
            "issues": issues_count
        }

    def _sync_project_metadata(self, key: str) -> Optional[SonarProject]:
        """同步项目元数据并维护映射关系。"""
        p_data = self.client.get_project(key)
        if not p_data:
            return None
            
        self.save_to_staging(source='sonarqube', entity_type='project', external_id=key, payload=p_data)
        
        project = self.session.query(SonarProject).filter_by(key=key).first()
        if not project:
            project = SonarProject(key=key)
            self.session.add(project)
            
        project.name = p_data.get('name')
        project.qualifier = p_data.get('qualifier')
        project.last_analysis_date = parse_iso8601(p_data.get('lastAnalysisDate'))
        
        # 自动关联 GitLab 项目
        if GitLabProject and (not project.gitlab_project_id):
            gitlab_project = self.session.query(GitLabProject).filter_by(path_with_namespace=key).first()
            if gitlab_project:
                project.gitlab_project_id = gitlab_project.id
        return project

    def _sync_measures(self, project: SonarProject):
        """同步代码质量指标。"""
        measures_data = self.client.get_measures(project.key)
        if not measures_data:
            return None
            
        gate_status = self.client.get_quality_gate_status(project.key)
        issue_dist = self.client.get_issue_severity_distribution(project.key)
        hotspot_dist = self.client.get_hotspot_distribution(project.key)
        
        measure = self.transformer.transform_measures_snapshot(
            project, measures_data, gate_status, issue_dist, hotspot_dist
        )
        self.session.add(measure)
        return measure

    def _sync_issues(self, project: SonarProject) -> int:
        """分页同步问题详情。"""
        count = 0
        page = 1
        while True:
            issues_data = self.client.get_issues(project.key, page=page)
            if not issues_data:
                break
            for i_data in issues_data:
                self.transformer.transform_issue(project, i_data)
                count += 1
            page += 1
            if count % 200 == 0:
                self.session.flush() # 提高内存效率
        return count

PluginRegistry.register_worker('sonarqube', SonarQubeWorker)
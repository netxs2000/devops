"""GitLab Worker Pipeline Mixin.

提供 Pipeline 和 Deployment 的同步逻辑。
"""
import logging
from datetime import datetime
from typing import List

from devops_collector.core.utils import parse_iso8601
from devops_collector.plugins.gitlab.models import Project, Pipeline, Deployment

logger = logging.getLogger(__name__)


class PipelineMixin:
    """提供流水线与部署相关的同步逻辑。
    
    负责同步 CI/CD 流水线 (Pipeline) 和 部署记录 (Deployment) 的数据。
    """

    def _sync_pipelines(self, project: Project) -> int:
        """从项目同步流水线记录。
        
        Args:
            project (Project): 关联的项目实体。
            
        Returns:
            int: 处理的流水线总数。
        """
        return self._process_generator(
            self.client.get_project_pipelines(project.id),
            lambda batch: self._save_pipelines_batch(project, batch)
        )

    def _save_pipelines_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存流水线及其基本指标。
        
        此方法包含两个步骤：
        1. 将原始数据保存到 Staging 表。
        2. 将数据转换并保存到业务模型表 (Pipeline)。
        
        Args:
            project (Project): 关联的项目实体。
            batch (List[dict]): 流水线原始数据列表。
        """
        # 1. Staging
        for data in batch:
            self.save_to_staging(
                source='gitlab',
                entity_type='pipeline',
                external_id=data['id'],
                payload=data,
                schema_version=self.SCHEMA_VERSION
            )
        
        # 2. Transform
        self._transform_pipelines_batch(project, batch)

    def _transform_pipelines_batch(self, project: Project, batch: List[dict]) -> None:
        """从原始数据转换并加载 Pipeline 实体。
        
        Args:
            project (Project): 关联的项目实体。
            batch (List[dict]): 流水线原始数据列表。
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(Pipeline).filter(Pipeline.id.in_(ids)).all()
        existing_map = {p.id: p for p in existing}
        
        for data in batch:
            p = existing_map.get(data['id'])
            if not p:
                p = Pipeline(id=data['id'])
                self.session.add(p)
            
            p.project_id = project.id
            p.status = data['status']
            p.ref = data.get('ref')
            p.sha = data.get('sha')
            p.source = data.get('source')
            p.created_at = parse_iso8601(data.get('created_at'))
            p.updated_at = parse_iso8601(data.get('updated_at'))
            p.coverage = data.get('coverage')

    def _sync_deployments(self, project: Project) -> int:
        """同步部署记录。
        
        Args:
            project (Project): 关联的项目实体。
            
        Returns:
            int: 处理的部署记录总数。
        """
        return self._process_generator(
            self.client.get_project_deployments(project.id),
            lambda batch: self._save_deployments_batch(project, batch)
        )
    
    def _save_deployments_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存部署信息。
        
        包含 Staging 和 Transform 两个阶段。
        
        Args:
            project (Project): 关联的项目实体。
            batch (List[dict]): 部署记录原始数据列表。
        """
        # 1. Staging
        for data in batch:
            self.save_to_staging(
                source='gitlab',
                entity_type='deployment',
                external_id=data['id'],
                payload=data,
                schema_version=self.SCHEMA_VERSION
            )
            
        # 2. Transform
        self._transform_deployments_batch(project, batch)

    def _transform_deployments_batch(self, project: Project, batch: List[dict]) -> None:
        """从原始数据转换并加载 Deployment 实体。
        
        Args:
            project (Project): 关联的项目实体。
            batch (List[dict]): 部署记录原始数据列表。
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(Deployment).filter(Deployment.id.in_(ids)).all()
        existing_map = {d.id: d for d in existing}
        
        for data in batch:
            d = existing_map.get(data['id'])
            if not d:
                d = Deployment(id=data['id'])
                self.session.add(d)
                
            d.project_id = project.id
            d.iid = data['iid']
            d.status = data['status']
            d.environment = data.get('environment', {}).get('name')
            d.created_at = parse_iso8601(data.get('created_at'))
            d.updated_at = parse_iso8601(data.get('updated_at'))
            d.ref = data.get('ref')
            d.sha = data.get('sha')

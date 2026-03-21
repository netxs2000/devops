"""GitLab Worker Pipeline Mixin.

提供 Pipeline 和 Deployment 的同步逻辑。
"""

import logging

from devops_collector.core.utils import parse_iso8601

from ..models import GitLabDeployment, GitLabPipeline, GitLabProject


logger = logging.getLogger(__name__)


class PipelineMixin:
    """提供流水线与部署相关的同步逻辑。

    负责同步 CI/CD 流水线 (Pipeline) 和 部署记录 (Deployment) 的数据。
    """

    def _sync_pipelines(self, project: GitLabProject) -> int:
        """从项目同步流水线记录。

        Args:
            project (GitLabProject): 关联的项目实体。

        Returns:
            int: 处理的流水线总数。
        """
        return self._process_generator(self.client.get_project_pipelines(project.id), lambda batch: self._save_pipelines_batch(project, batch))

    def _save_pipelines_batch(self, project: GitLabProject, batch: list[dict]) -> None:
        """批量保存流水线及其基本指标。

        此方法包含两个步骤：
        1. 将原始数据保存到 Staging 表 (COPY FROM 批量)。
        2. 将数据转换并保存到业务模型表 (Pipeline)。

        Args:
            project (GitLabProject): 关联的项目实体。
            batch (List[dict]): 流水线原始数据列表。
        """
        self.bulk_save_to_staging("gitlab", "pipeline", batch)
        self._transform_pipelines_batch(project, batch)

    def _transform_pipelines_batch(self, project: GitLabProject, batch: list[dict]) -> None:
        """从原始数据转换并加载 Pipeline 实体。

        Args:
            project (GitLabProject): 关联的项目实体。
            batch (List[dict]): 流水线原始数据列表。
        """
        ids = [item["id"] for item in batch]
        existing = self.session.query(GitLabPipeline).filter(GitLabPipeline.id.in_(ids)).all()
        existing_map = {p.id: p for p in existing}
        for data in batch:
            p = existing_map.get(data["id"])
            if not p:
                p = GitLabPipeline(id=data["id"])
                self.session.add(p)
            p.project_id = project.id
            p.status = data["status"]
            p.ref = data.get("ref")
            p.sha = data.get("sha")
            p.source = data.get("source")
            p.created_at = parse_iso8601(data.get("created_at"))
            p.updated_at = parse_iso8601(data.get("updated_at"))
            p.coverage = data.get("coverage")

    def _sync_deployments(self, project: GitLabProject) -> int:
        """同步部署记录。

        Args:
            project (GitLabProject): 关联的项目实体。

        Returns:
            int: 处理的部署记录总数。
        """
        return self._process_generator(self.client.get_project_deployments(project.id), lambda batch: self._save_deployments_batch(project, batch))

    def _save_deployments_batch(self, project: GitLabProject, batch: list[dict]) -> None:
        """批量保存部署信息。

        包含 Staging (COPY FROM 批量) 和 Transform 两个阶段。

        Args:
            project (GitLabProject): 关联的项目实体。
            batch (List[dict]): 部署记录原始数据列表。
        """
        self.bulk_save_to_staging("gitlab", "deployment", batch)
        self._transform_deployments_batch(project, batch)

    def _transform_deployments_batch(self, project: GitLabProject, batch: list[dict]) -> None:
        """从原始数据转换并加载 Deployment 实体。

        Args:
            project (GitLabProject): 关联的项目实体。
            batch (List[dict]): 部署记录原始数据列表。
        """
        from devops_collector.config import settings

        ids = [item["id"] for item in batch]
        existing = self.session.query(GitLabDeployment).filter(GitLabDeployment.id.in_(ids)).all()
        existing_map = {d.id: d for d in existing}
        
        # 获取生产环境关键词配置
        prod_envs = settings.analysis.production_env_mapping
        if isinstance(prod_envs, str):
            prod_envs = [i.strip() for i in prod_envs.split(",")]

        for data in batch:
            d = existing_map.get(data["id"])
            if not d:
                d = GitLabDeployment(id=data["id"])
                self.session.add(d)
                
            d.project_id = project.id
            d.mdm_project_id = project.mdm_project_id
            d.iid = data["iid"]
            d.status = data["status"]
            d.environment = data.get("environment", {}).get("name")
            d.created_at = parse_iso8601(data.get("created_at"))
            d.updated_at = parse_iso8601(data.get("updated_at"))
            d.ref = data.get("ref")
            d.sha = data.get("sha")
            
            # 识别是否为生产环境部署
            if d.environment:
                d.is_production = any(p.lower() in d.environment.lower() for p in prod_envs)
            
            # 标记为可见 (Option A), 部署数据通常直接用于分析，这里设为当前转正
            if d.status == "success":
                from datetime import datetime
                d.promoted_at = datetime.now()

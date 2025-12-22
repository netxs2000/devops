"""GitLab Worker Merge Request Mixin.

提供 MR 及其相关分析逻辑。
"""
import logging
from datetime import datetime
from typing import List, Optional

from devops_collector.core.utils import parse_iso8601
from devops_collector.plugins.gitlab.models import Project, MergeRequest

logger = logging.getLogger(__name__)


class MergeRequestMixin:
    """提供 MR 相关的同步逻辑。
    
    包含 MR 的基础信息同步、数据转换以及深度协作分析功能。
    """

    def _sync_merge_requests(self, project: Project, since: Optional[str]) -> int:
        """从项目同步合并请求 (MR)。

        Args:
            project (Project): 关联的项目实体。
            since (Optional[str]): ISO 格式时间字符串，仅同步该时间后的 MR。

        Returns:
            int: 同步处理的 MR 总数。
        """
        return self._process_generator(
            self.client.get_project_merge_requests(project.id, since=since),
            lambda batch: self._save_mrs_batch(project, batch)
        )

    def _save_mrs_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存合并请求记录。
        
        第一阶段：Extract & Load (Staging) - 原始数据落盘
        第二阶段：Transform & Load (DW) - 业务逻辑解析

        Args:
            project (Project): 关联的项目实体。
            batch (List[dict]): 包含多个 MR 原始数据的列表。
        """
        # 1. 采集落盘 (ODS 层)
        for data in batch:
            self.save_to_staging(
                source='gitlab',
                entity_type='merge_request',
                external_id=data['id'],
                payload=data,
                schema_version=self.SCHEMA_VERSION
            )
        
        # 2. 转换加载 (DW 层)
        self._transform_mrs_batch(project, batch)

    def _transform_mrs_batch(self, project: Project, batch: List[dict]) -> None:
        """核心解析逻辑：将原始 JSON 转换为 MergeRequest 模型。

        Args:
            project (Project): 关联的项目实体。
            batch (List[dict]): 包含多个 MR 原始数据的列表。
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(MergeRequest).filter(MergeRequest.id.in_(ids)).all()
        existing_map = {m.id: m for m in existing}
        
        for data in batch:
            mr = existing_map.get(data['id'])
            if not mr:
                mr = MergeRequest(id=data['id'])
                self.session.add(mr)
            
            mr.project_id = project.id
            mr.iid = data['iid']
            mr.title = data['title']
            mr.description = data.get('description')
            mr.state = data['state']
            mr.author_username = data.get('author', {}).get('username')
            mr.created_at = parse_iso8601(data['created_at'])
            mr.updated_at = parse_iso8601(data['updated_at'])
            mr.merge_commit_sha = data.get('merge_commit_sha')
            
            if data.get('merged_at'):
                mr.merged_at = parse_iso8601(data['merged_at'])
            if data.get('closed_at'):
                mr.closed_at = parse_iso8601(data['closed_at'])
                
            if data.get('author'):
                if self.user_resolver:
                    uid = self.user_resolver.resolve(data['author']['id'])
                    mr.author_id = uid
            
            # 自动化链路追踪提取 (via TraceabilityMixin)
            if hasattr(self, '_apply_traceability_extraction'):
                self._apply_traceability_extraction(mr)
            
            # 行为特征：协作深度与评审质量
            if self.enable_deep_analysis or mr.state in ('merged', 'opened'):
                # 注意：这也是 Side Effect，需要 API 调用
                if hasattr(self, 'client'): 
                    self._apply_mr_collaboration_analysis(project, mr)

    def _apply_mr_collaboration_analysis(self, project: Project, mr: MergeRequest) -> None:
        """分析合并请求的协作深度与评审质量。
        
        此方法会调用多个 API 端点以获取审批、评论和流水线信息，
        用于计算 Review Cycles, First Response Time 等效能指标。

        Args:
            project (Project): 关联的项目实体。
            mr (MergeRequest): 要分析的合并请求对象。
        """
        try:
            # 1. 获取审批数
            approvals = self.client.get_mr_approvals(project.id, mr.iid)
            mr.approval_count = len(approvals.get('approved_by', []))
            
            # 2. 获取评论与首次响应
            notes = list(self.client.get_mr_notes(project.id, mr.iid))
            human_notes = [n for n in notes if n.get('system') is False]
            mr.human_comment_count = len(human_notes)
            
            if human_notes:
                # 按创建时间排序
                human_notes.sort(key=lambda x: x['created_at'])
                first_note_at = parse_iso8601(human_notes[0]['created_at'])
                mr.first_response_at = first_note_at
            
            # 3. 计算评审周期
            system_notes = [n for n in notes if n.get('system') is True]
            updated_commits_notes = [n for n in system_notes if "added" in n.get('body', "").lower() and "commit" in n.get('body', "").lower()]
            mr.review_cycles = 1 + len(updated_commits_notes)
            
            # 4. 计算评审耗时
            if mr.merged_at and mr.created_at:
                delta = mr.merged_at - mr.created_at
                mr.review_time_total = int(delta.total_seconds())
                
            # 5. 质量门禁状态
            pipelines = self.client.get_mr_pipelines(project.id, mr.iid)
            if pipelines:
                latest_p = pipelines[0]
                mr.quality_gate_status = 'passed' if latest_p.get('status') == 'success' else 'failed'

        except Exception as e:
            logger.warning(f"Failed to analyze MR collaboration for {mr.iid}: {e}")

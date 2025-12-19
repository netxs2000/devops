"""GitLab Worker Traceability Mixin.

提供跨工具链的追溯链路提取能力。
"""
import re
import logging
from typing import List, Any
from devops_collector.models.base_models import TraceabilityLink
from devops_collector.plugins.gitlab.models import Commit, MergeRequest

logger = logging.getLogger(__name__)


class TraceabilityMixin:
    """提供链路追溯提取逻辑。"""

    def _apply_traceability_extraction(self, obj: Any) -> None:
        """从项目对象（Commit/MR）的文本内容中提取业务需求追溯信息。
        
        支持正则匹配:
        - Jira: [A-Z]+-\d+ (如 PROJ-123)
        - ZenTao: #\d+ (如 #456)
        
        Args:
            obj (Any): 提交记录 (Commit) 或合并请求 (MergeRequest) 实体。
        """
        text_to_scan = ""
        if isinstance(obj, Commit):
            text_to_scan = f"{obj.title}\n{obj.message}"
        elif isinstance(obj, MergeRequest):
            text_to_scan = f"{obj.title}\n{obj.description or ''}"
        
        if not text_to_scan:
            return

        # 1. 匹配 Jira (大写字母+横线+数字)
        jira_matches = list(set(re.findall(r'([A-Z]{2,}-\d+)', text_to_scan)))
        # 2. 匹配 ZenTao (井号+数字)
        zentao_matches = list(set(re.findall(r'#(\d+)', text_to_scan)))

        # 更新对象字段并建立 TraceabilityLink
        if jira_matches:
            self._save_traceability_results(obj, jira_matches, 'jira', text_to_scan)
        
        if zentao_matches:
            self._save_traceability_results(obj, zentao_matches, 'zentao', text_to_scan)

    def _save_traceability_results(self, obj: Any, ids: List[str], source: str, text_content: str = None) -> None:
        """保存提取到的追溯 ID 到对象并创建映射表记录。
        
        Args:
            obj (Any): 目标实体对象。
            ids (List[str]): 提取到的外部 ID 列表。
            source (str): 来源系统类型 (jira, zentao)。
            text_content (str): 原始文本内容，用于存证。
        """
        if isinstance(obj, MergeRequest):
            # MR 通常只关联一个主需求，取第一个
            if not obj.external_issue_id: # 避免覆盖
                obj.external_issue_id = ids[0]
                obj.issue_source = source
        elif isinstance(obj, Commit):
            # Commit 支持关联多个需求
            if not obj.linked_issue_ids:
                obj.linked_issue_ids = []
            
            # 合并并去重
            current_ids = set(obj.linked_issue_ids)
            current_ids.update(ids)
            obj.linked_issue_ids = list(current_ids)
            obj.issue_source = source

        # 创建通用追溯链路记录
        target_type = 'commit' if isinstance(obj, Commit) else 'mr'
        target_id = obj.id if isinstance(obj, Commit) else str(obj.iid)

        for ext_id in ids:
            # 幂等检查：防止重复插入链路记录
            existing = self.session.query(TraceabilityLink).filter_by(
                source_system=source,
                source_id=ext_id,
                target_system='gitlab',
                target_type=target_type,
                target_id=target_id
            ).first()

            if not existing:
                link = TraceabilityLink(
                    source_system=source,
                    source_type='task' if source == 'zentao' else 'issue',
                    source_id=ext_id,
                    target_system='gitlab',
                    target_type=target_type,
                    target_id=target_id,
                    link_type='fixes',
                    raw_data={'auto_extracted': True, 'found_in': text_content[:200] if text_content else None}
                )
                self.session.add(link)

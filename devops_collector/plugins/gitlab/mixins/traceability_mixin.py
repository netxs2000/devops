"""GitLab Worker Traceability Mixin.

提供跨工具链的追溯链路提取能力。
"""
import re
import logging
from typing import List, Any
from devops_collector.models.base_models import TraceabilityLink
from ..models import GitLabCommit, GitLabMergeRequest
logger = logging.getLogger(__name__)

class TraceabilityMixin:
    """提供链路追溯提取逻辑。
    
    能够从 Commit Message 或 MR Description 中提取 Jira/ZenTao 等外部系统的单号，
    并建立 TraceabilityLink 关联。
    """

    def _apply_traceability_extraction(self, obj: Any) -> None:
        """从项目对象（GitLabCommit/MR）的文本内容中提取业务需求追溯信息。
        
        支持正则匹配:
        - Jira: [A-Z]+-\\d+ (如 PROJ-123)
        - ZenTao: #\\d+ (如 #456)
        
        提取到的 ID 会更新到对象的 metadata 中，并创建 TraceabilityLink 记录。
        
        Args:
            obj (Any): 提交记录 (GitLabCommit) 或合并请求 (GitLabMergeRequest) 实体。
        """
        text_to_scan = ''
        if isinstance(obj, GitLabCommit):
            text_to_scan = f'{obj.title}\n{obj.message}'
        elif isinstance(obj, GitLabMergeRequest):
            text_to_scan = f"{obj.title}\n{obj.description or ''}"
        if not text_to_scan:
            return
        jira_matches = list(set(re.findall('([A-Z]{2,}-\\d+)', text_to_scan)))
        zentao_matches = list(set(re.findall('#(\\d+)', text_to_scan)))
        if jira_matches:
            self._save_traceability_results(obj, jira_matches, 'jira', text_to_scan)
        if zentao_matches:
            self._save_traceability_results(obj, zentao_matches, 'zentao', text_to_scan)

    def _save_traceability_results(self, obj: Any, ids: List[str], source: str, text_content: str=None) -> None:
        """保存提取到的追溯 ID 到对象并创建映射表记录。
        
        Args:
            obj (Any): 目标实体对象 (GitLabCommit 或 GitLabMergeRequest)。
            ids (List[str]): 提取到的外部 ID 列表。
            source (str): 来源系统类型 (jira, zentao)。
            text_content (str): 原始文本内容，用于存证 (截取前200字符)。
        """
        if isinstance(obj, GitLabMergeRequest):
            if not obj.external_issue_id:
                obj.external_issue_id = ids[0]
                obj.issue_source = source
        elif isinstance(obj, GitLabCommit):
            if not obj.linked_issue_ids:
                obj.linked_issue_ids = []
            current_ids = set(obj.linked_issue_ids)
            current_ids.update(ids)
            obj.linked_issue_ids = list(current_ids)
            obj.issue_source = source
        target_type = 'commit' if isinstance(obj, GitLabCommit) else 'mr'
        target_id = obj.id if isinstance(obj, GitLabCommit) else str(obj.iid)
        for ext_id in ids:
            existing = self.session.query(TraceabilityLink).filter_by(source_system=source, source_id=ext_id, target_system='gitlab', target_type=target_type, target_id=target_id).first()
            if not existing:
                link = TraceabilityLink(source_system=source, source_type='task' if source == 'zentao' else 'issue', source_id=ext_id, target_system='gitlab', target_type=target_type, target_id=target_id, link_type='fixes', raw_data={'auto_extracted': True, 'found_in': text_content[:200] if text_content else None})
                self.session.add(link)
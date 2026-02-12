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

        # 1. 提取 Jira ID (如 PROJ-123)
        jira_matches = list(set(re.findall(r'([A-Z]{2,}-\d+)', text_to_scan)))
        if jira_matches:
            self._save_traceability_results(obj, jira_matches, 'jira', text_to_scan)

        # 2. 提取禅道 ID (支持 #123 规范)
        # 使用正向和负向预查避免匹配到 C# 或类似的非单号内容
        zentao_matches = re.findall(r'(?<!\w)#(\d+)(?!\w)', text_to_scan)
        if zentao_matches:
            # 保持原始顺序以便识别“第一个”ID，同时去重
            seen = set()
            ordered_zentao_ids = []
            for zid in zentao_matches:
                if zid not in seen:
                    ordered_zentao_ids.append(zid)
                    seen.add(zid)
            
            self._save_traceability_results(obj, ordered_zentao_ids, 'zentao', text_to_scan)

    def _save_traceability_results(self, obj: Any, ids: List[str], source: str, text_content: str=None) -> None:
        """保存提取到的追溯 ID 到对象并创建映射表记录。
        
        逻辑规则:
        1. 若有多个 ID，对象主字段仅保存第一个。
        2. 追溯表 (TraceabilityLink) 保存所有发现的 ID。
        3. 即使目标 ID 在本地尚未同步，也允许建立关联（标记为自动提取）。
        
        Args:
            obj (Any): 目标实体对象 (GitLabCommit 或 GitLabMergeRequest)。
            ids (List[str]): 提取到的外部 ID 列表。
            source (str): 来源系统类型 (jira, zentao)。
            text_content (str): 原始文本内容，用于存证 (截取前200字符)。
        """
        if not ids:
            return

        # 更新对象主字段 (仅存第一个匹配到的 ID)
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

        # 存储到追溯表 (保存全部 ID)
        target_type = 'commit' if isinstance(obj, GitLabCommit) else 'mr'
        target_id = str(obj.id) if isinstance(obj, GitLabCommit) else str(obj.iid)
        
        for ext_id in ids:
            # 检查是否已存在相同的关联，防止重复插入
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
                    link_type='fixes' if source == 'zentao' else 'implements',
                    raw_data={
                        'auto_extracted': True, 
                        'found_in': text_content[:200] if text_content else None,
                        'is_tentative': True # 标记为初步关联，待主数据验证
                    }
                )
                self.session.add(link)

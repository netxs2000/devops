"""GitLab Worker Commit Mixin.

提供提交记录 (Commit) 的同步、落盘及 Diff 分析逻辑。
"""
import logging
from datetime import datetime
from typing import List, Optional
from devops_collector.core.utils import parse_iso8601
from devops_collector.plugins.gitlab.models import Project, Commit, CommitFileStats
from devops_collector.plugins.gitlab.analyzer import DiffAnalyzer
logger = logging.getLogger(__name__)

class CommitMixin:
    """提供 Commit 相关的同步逻辑。
    
    包含提交记录的批量同步、Staging 落盘、Diff 代码量统计及行为特征分析。
    """

    def _sync_commits(self, project: Project, since: Optional[str]) -> int:
        """同步项目的提交记录。
        
        使用生成器流式同步项目的 Git 提交。
        
        Args:
            project (Project): 项目实体对象。
            since (Optional[str]): ISO 格式的时间字符串，仅同步该时间之后的提交。
            
        Returns:
            int: 本次成功处理的提交总数。
        """
        return self._process_generator(self.client.get_project_commits(project.id, since=since), lambda batch: self._save_commits_batch(project, batch))

    def _save_commits_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存提交记录，并触发追溯与行为分析。

        流程包括：
        1. 过滤已存在的 Commit。
        2. 创建新 Commit 实体并保存基本统计 (additions, deletions)。
        3. 触发 Traceability 提取 (关联 Issue)。
        4. 触发行为特征分析 (加班识别)。
        5. (可选) 触发深度 Diff 分析。
        
        Args:
            project (Project): 关联的项目实体。
            batch (List[dict]): 从 API 获取的原始提交数据列表。
        """
        existing = self.session.query(Commit.id).filter(Commit.project_id == project.id, Commit.id.in_([c['id'] for c in batch])).all()
        existing_ids = {c.id for c in existing}
        new_commits = []
        for data in batch:
            if data['id'] in existing_ids:
                continue
            commit = Commit(id=data['id'], project_id=project.id, short_id=data['short_id'], title=data['title'], author_name=data['author_name'], author_email=data['author_email'], message=data['message'], authored_date=parse_iso8601(data['authored_date']), committed_date=parse_iso8601(data['committed_date']))
            stats = data.get('stats', {})
            commit.additions = stats.get('additions', 0)
            commit.deletions = stats.get('deletions', 0)
            commit.total = stats.get('total', 0)
            self.session.add(commit)
            new_commits.append(commit)
            if hasattr(self, '_apply_traceability_extraction'):
                self._apply_traceability_extraction(commit)
            self._apply_commit_behavior_analysis(commit)
        if self.enable_deep_analysis and new_commits:
            for commit in new_commits:
                self._process_commit_diffs(project, commit)

    def _process_commit_diffs(self, project: Project, commit: Commit) -> None:
        """分析 Commit 的 Diff 并分类统计文件变更。
        
        提取每次提交中具体文件的代码、注释和空行变更数量，并识别文件所属的技术栈。
        此操作涉及额外的 API 调用，仅在 enable_deep_analysis=True 时执行。
        
        Args:
            project (Project): 关联的项目实体。
            commit (Commit): 需要分析的提交对象。
        """
        try:
            diffs = self.client.get_commit_diff(project.id, commit.id)
            for diff in diffs:
                file_path = diff.get('new_path') or diff.get('old_path')
                if not file_path or DiffAnalyzer.is_ignored(file_path):
                    continue
                diff_text = diff.get('diff', '')
                stats = DiffAnalyzer.analyze_diff(diff_text, file_path)
                category = DiffAnalyzer.get_file_category(file_path)
                file_stats = CommitFileStats(commit_id=commit.id, file_path=file_path, file_type_category=category, **stats)
                self.session.add(file_stats)
        except Exception as e:
            logger.warning(f'Failed to analyze diff for commit {commit.id}: {e}')

    def _apply_commit_behavior_analysis(self, commit: Commit) -> None:
        """分析 Commit 的行为特征（主要检测是否为非工作时间提交）。

        Args:
            commit (Commit): 待分析的提交对象。
        """
        if not commit.committed_date:
            return
        dt = commit.committed_date
        is_weekend = dt.weekday() >= 5
        is_night = dt.hour >= 20 or dt.hour < 8
        commit.is_off_hours = is_weekend or is_night
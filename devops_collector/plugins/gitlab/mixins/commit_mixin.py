"""GitLab Worker Commit Mixin.

提供提交记录 (Commit) 的同步、落盘及 Diff 分析逻辑。
"""
import logging
from datetime import datetime
from typing import List, Optional
from devops_collector.core.utils import parse_iso8601
from ..models import GitLabProject, GitLabCommit, GitLabCommitFileStats
from devops_collector.core.analytics.eloc import ELOCAnalyzer, ELOCOptions
from devops_collector.models.base_models import CommitMetrics # Import Core Model
import pytz
from dateutil import parser
logger = logging.getLogger(__name__)

class CommitMixin:
    """提供 GitLabCommit 相关的同步逻辑。
    
    包含提交记录的批量同步、Staging 落盘、Diff 代码量统计及行为特征分析。
    """

    def _sync_commits(self, project: GitLabProject, since: Optional[str]) -> int:
        """同步项目的提交记录。
        
        使用生成器流式同步项目的 Git 提交。
        
        Args:
            project (GitLabProject): 项目实体对象。
            since (Optional[str]): ISO 格式的时间字符串，仅同步该时间之后的提交。
            
        Returns:
            int: 本次成功处理的提交总数。
        """
        return self._process_generator(self.client.get_project_commits(project.id, since=since), lambda batch: self._save_commits_batch(project, batch))

    def _save_commits_batch(self, project: GitLabProject, batch: List[dict]) -> None:
        """批量保存提交记录，并触发追溯与行为分析。

        流程包括：
        1. 过滤已存在的 GitLabCommit。
        2. 创建新 GitLabCommit 实体并保存基本统计 (additions, deletions)。
        3. 触发 Traceability 提取 (关联 Issue)。
        4. 触发行为特征分析 (加班识别)。
        5. (可选) 触发深度 Diff 分析。
        
        Args:
            project (GitLabProject): 关联的项目实体。
            batch (List[dict]): 从 API 获取的原始提交数据列表。
        """
        existing = self.session.query(GitLabCommit.id).filter(GitLabCommit.project_id == project.id, GitLabCommit.id.in_([c['id'] for c in batch])).all()
        existing_ids = {c.id for c in existing}
        new_commits = []
        for data in batch:
            if data['id'] in existing_ids:
                continue
            commit = GitLabCommit(id=data['id'], project_id=project.id, short_id=data['short_id'], title=data['title'], author_name=data['author_name'], author_email=data['author_email'], message=data['message'], authored_date=parse_iso8601(data['authored_date']), committed_date=parse_iso8601(data['committed_date']))
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

    def _process_commit_diffs(self, project: GitLabProject, commit: GitLabCommit) -> None:
        """分析 GitLabCommit 的 Diff 并计算 ELOC / Impact / Churn。
        
        升级版逻辑 (v2.0)：
        1. 使用 ELOCAnalyzer 替代简单的 DiffAnalyzer。
        2. 调用 get_file_last_commit 获取文件上次变更时间，用于判定 Churn (短期重写) 和 Legacy (老代码)。
        3. 聚合计算结果并写入核心数据表 commit_metrics (供 Streamlit 看板使用)。
        
        Args:
            project (GitLabProject): 关联的项目实体。
            commit (GitLabCommit): 需要分析的提交对象。
        """
        try:
            diffs = self.client.get_commit_diff(project.id, commit.id)
            analyzer = ELOCAnalyzer()
            
            # Aggregators for CommitMetrics
            total_eloc = 0.0
            total_impact = 0.0
            total_churn_lines = 0
            file_count = 0
            total_test_lines = 0.0
            total_comment_lines = 0.0
            
            # Pre-fetch commit time for Churn calculation
            commit_time = commit.committed_date
            if commit_time and not commit_time.tzinfo:
                commit_time = commit_time.replace(tzinfo=pytz.UTC)

            for diff in diffs:
                file_path = diff.get('new_path') or diff.get('old_path')
                
                # Basic Filtering
                if not file_path: continue
                # Use analyzer options to check if generated (basic check first to save API calls)
                if analyzer._is_generated(file_path): continue

                # --- 1. Fetch History for Churn/Legacy ---
                last_commit = self.client.get_file_last_commit(project.id, file_path, commit.id)
                last_mod_date = None
                is_churn = False
                
                if last_commit:
                    try:
                        last_mod_date = last_commit.get('committed_date')
                        # Check Churn: Modified within 21 days (approx 3 weeks)
                        if commit_time and last_mod_date:
                            prev_date = parser.isoparse(str(last_mod_date))
                            if not prev_date.tzinfo: prev_date = prev_date.replace(tzinfo=pytz.UTC)
                            
                            if (commit_time - prev_date).days <= 21 and (commit_time - prev_date).days >= 0:
                                is_churn = True
                    except Exception:
                        pass

                # --- 2. Run ELOC Analysis ---
                diff_text = diff.get('diff', '')
                diff_lines = diff_text.split('\n')
                
                # Call Core Algorithm
                result = analyzer.analyze_commit_diff(
                    file_path=file_path,
                    diff_lines=diff_lines,
                    file_last_modified_date=last_mod_date,
                    is_churn_commit=is_churn
                )
                
                # --- 3. Save File Stats (Legacy Plugin Model - Optional but kept for compatibility) ---
                # mapping ELOC result back to old GitLabCommitFileStats fields where possible
                # Note: This is partial mapping as old mode didn't have impact/churn.
                # We prioritize the NEW CommitMetrics table below.
                file_stats = GitLabCommitFileStats(
                    commit_id=commit.id,
                    file_path=file_path,
                    language=None, # DiffAnalyzer had this, ELOCAnalyzer currently infers basic types
                    file_type_category='Test' if result.test_lines > 0 else 'Source', 
                    code_added=result.raw_additions,
                    code_deleted=result.raw_deletions,
                    comment_added=result.comment_lines
                )
                self.session.add(file_stats)
                
                # --- 4. Aggregate Totals ---
                total_eloc += result.eloc_score
                total_impact += result.impact_score
                total_churn_lines += result.churn_lines
                total_test_lines += result.test_lines
                total_comment_lines += result.comment_lines
                if result.raw_additions > 0 or result.raw_deletions > 0:
                    file_count += 1

            # --- 5. Persist to Core CommitMetrics (For Streamlit) ---
            # Create or Update
            metrics = self.session.query(CommitMetrics).filter_by(commit_id=commit.id).first()
            if not metrics:
                metrics = CommitMetrics(commit_id=commit.id)
            
            metrics.project_id = str(project.id) # Ensure string format
            metrics.author_email = commit.author_email
            metrics.committed_at = commit.committed_date
            metrics.raw_additions = commit.additions
            metrics.raw_deletions = commit.deletions
            
            # New Advanced Metrics
            metrics.eloc_score = total_eloc
            metrics.impact_score = total_impact
            metrics.churn_lines = total_churn_lines
            metrics.file_count = file_count
            metrics.test_lines = int(total_test_lines)
            metrics.comment_lines = int(total_comment_lines)
            
            # Simple Refactor Ratio Approximation (Deletions / Total Changes)
            total_changes = commit.additions + commit.deletions
            metrics.refactor_ratio = (commit.deletions / total_changes) if total_changes > 0 else 0.0
            
            self.session.add(metrics)
            
            # Also update the original GitLabCommit object with summary data if needed
            commit.total = total_changes

        except Exception as e:
            logger.warning(f'Failed to analyze diff for commit {commit.id}: {e}')

    def _apply_commit_behavior_analysis(self, commit: GitLabCommit) -> None:
        """分析 GitLabCommit 的行为特征（主要检测是否为非工作时间提交）。

        Args:
            commit (GitLabCommit): 待分析的提交对象。
        """
        if not commit.committed_date:
            return
        dt = commit.committed_date
        is_weekend = dt.weekday() >= 5
        is_night = dt.hour >= 20 or dt.hour < 8
        commit.is_off_hours = is_weekend or is_night
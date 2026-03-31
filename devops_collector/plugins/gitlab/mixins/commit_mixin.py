"""GitLab Worker Commit Mixin.

提供提交记录 (Commit) 的同步、落盘及 Diff 分析逻辑。
"""

import logging

import pytz
from dateutil import parser

from devops_collector.core.analytics.eloc import ELOCAnalyzer
from devops_collector.core.utils import parse_iso8601

from ..models import GitLabCommit, GitLabCommitFileStats, GitLabProject


logger = logging.getLogger(__name__)


class CommitMixin:
    """提供 GitLabCommit 相关的同步逻辑。

    包含提交记录的批量同步、Staging 落盘、Diff 代码量统计及行为特征分析。
    """

    def _sync_commits(self, project: GitLabProject, since: str | None) -> int:
        """同步项目的提交记录。

        使用生成器流式同步项目的 Git 提交。

        Args:
            project (GitLabProject): 项目实体对象。
            since (Optional[str]): ISO 格式的时间字符串，仅同步该时间之后的提交。

        Returns:
            int: 本次成功处理的提交总数。
        """
        return self._process_generator(
            self.client.get_project_commits(project.id, since=since),
            lambda batch: self._save_commits_batch(project, batch),
        )

    def _save_commits_batch(self, project: GitLabProject, batch: list[dict]) -> None:
        """批量保存提交记录，并触发追溯与行为分析。

        优化：直接使用 COPY 接管 Staging 落盘，并通过 PostreSQL On-Conflict 替换查改逻辑。
        """
        # 1. 采用 Staging 落盘 (BaseWorker 内部已处理方言兼容)
        self.bulk_save_to_staging("gitlab", "commit", batch)

        if not batch:
            return

        dialect = self.session.bind.dialect.name
        commit_objs = []
        insert_values = []

        for data in batch:
            commit = GitLabCommit(
                id=data["id"],
                project_id=project.id,
                short_id=data.get("short_id"),
                title=data.get("title", ""),
                author_name=data.get("author_name", "Unknown"),
                author_email=data.get("author_email"),
                message=data.get("message", ""),
                authored_date=parse_iso8601(data.get("authored_date") or data.get("created_at")),
                committed_date=parse_iso8601(data.get("committed_date") or data.get("created_at")),
            )
            stats = data.get("stats", {})
            commit.additions = stats.get("additions", 0)
            commit.deletions = stats.get("deletions", 0)
            commit.total = stats.get("total", 0)

            if hasattr(self, "_apply_traceability_extraction"):
                self._apply_traceability_extraction(commit)
            self._apply_commit_behavior_analysis(commit)

            insert_values.append(
                {
                    "id": commit.id,
                    "project_id": commit.project_id,
                    "short_id": commit.short_id,
                    "title": commit.title,
                    "author_name": commit.author_name,
                    "author_email": commit.author_email,
                    "message": commit.message,
                    "authored_date": commit.authored_date,
                    "committed_date": commit.committed_date,
                    "additions": commit.additions,
                    "deletions": commit.deletions,
                    "total": commit.total,
                    "is_off_hours": commit.is_off_hours,
                    "linked_issue_ids": getattr(commit, "linked_issue_ids", None),
                    "issue_source": getattr(commit, "issue_source", None),
                    "gitlab_user_id": getattr(commit, "gitlab_user_id", None),
                }
            )
            commit_objs.append(commit)

        new_commits = []
        if insert_values:
            if dialect == "postgresql":
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                # 2. 使用原生 ON CONFLICT 避免读写竞争击穿
                stmt = pg_insert(GitLabCommit).values(insert_values)
                stmt = stmt.on_conflict_do_nothing(index_elements=["id"]).returning(GitLabCommit.id)
                result = self.session.execute(stmt)
                inserted_ids = {row[0] for row in result.fetchall()}
                new_commits = [c for c in commit_objs if c.id in inserted_ids]
            else:
                # SQLite/Other 降级方案：逐条 merge
                for commit in commit_objs:
                    # 使用 merge 确保幂等性且不抛出 Duplicate Key 错误
                    # 在集成测试环境下性能可接受
                    self.session.merge(commit)
                    new_commits.append(commit)
                self.session.flush()

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
                file_path = diff.get("new_path") or diff.get("old_path")

                # Basic Filtering
                if not file_path:
                    continue
                # Use analyzer options to check if generated (basic check first to save API calls)
                if analyzer._is_generated(file_path):
                    continue

                # --- 1. Fetch History for Churn/Legacy ---
                last_commit = self.client.get_file_last_commit(project.id, file_path, commit.id)
                last_mod_date = None
                is_churn = False

                if last_commit:
                    try:
                        last_mod_date = last_commit.get("committed_date")
                        # Check Churn: Modified within 21 days (approx 3 weeks)
                        if commit_time and last_mod_date:
                            prev_date = parser.isoparse(str(last_mod_date))
                            if not prev_date.tzinfo:
                                prev_date = prev_date.replace(tzinfo=pytz.UTC)

                            if (commit_time - prev_date).days <= 21 and (commit_time - prev_date).days >= 0:
                                is_churn = True
                    except Exception:
                        pass

                # --- 2. Run ELOC Analysis ---
                diff_text = diff.get("diff", "")
                diff_lines = diff_text.split("\n")

                # Call Core Algorithm
                result = analyzer.analyze_commit_diff(
                    file_path=file_path,
                    diff_lines=diff_lines,
                    file_last_modified_date=last_mod_date,
                    is_churn_commit=is_churn,
                )

                # --- 3. Save File Stats (Legacy Plugin Model - Optional but kept for compatibility) ---
                # mapping ELOC result back to old GitLabCommitFileStats fields where possible
                # Note: This is partial mapping as old mode didn't have impact/churn.
                # We prioritize the NEW CommitMetrics table below.
                file_stats = GitLabCommitFileStats(
                    commit_id=commit.id,
                    file_path=file_path,
                    language=None,  # DiffAnalyzer had this, ELOCAnalyzer currently infers basic types
                    file_type_category="Test" if result.test_lines > 0 else "Source",
                    code_added=result.raw_additions,
                    code_deleted=result.raw_deletions,
                    comment_added=result.comment_lines,
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

            # --- 5. Persist to Plugin-Specific GitLabCommit fields (Decoupled from Core) ---
            commit.eloc_score = total_eloc
            commit.impact_score = total_impact
            commit.churn_lines = total_churn_lines
            commit.file_count = file_count
            commit.test_lines = int(total_test_lines)
            commit.comment_lines = int(total_comment_lines)

            # Simple Refactor Ratio Approximation (Deletions / Total Changes)
            total_changes = commit.additions + commit.deletions
            commit.refactor_ratio = (commit.deletions / total_changes) if total_changes > 0 else 0.0

            self.session.add(commit)

            # Also update the original GitLabCommit object with summary data if needed
            commit.total = total_changes

        except Exception as e:
            logger.warning(f"Failed to analyze diff for commit {commit.id}: {e}")

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

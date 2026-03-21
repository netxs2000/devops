"""devops_collector.core.promotion_service

数据转正服务 (Promotion Service)，负责将各插件采集的领域模型“提拔”为全局 MDM/Report 层模型。
这是架构审计 Option A 方案的核心实现，用于解耦同步 Worker 与主数据逻辑。
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from devops_collector.core.identity_manager import IdentityManager
from devops_collector.models.base_models import CommitMetrics
from devops_collector.plugins.gitlab.models import GitLabCommit


logger = logging.getLogger(__name__)


class PromotionService:
    """负责跨域数据转正与对齐的单例服务。"""

    @staticmethod
    def promote_gitlab_commits(session: Session, limit: int = 1000) -> int:
        """将 GitLab 提交记录转正到核心度量表。

        该过程包含：
        1. 关联主数据项目 (MDM Project ID)
        2. 通过 IdentityManager 解析 OneID (Global User ID)
        3. 同步 ELOC, Impact 等插件特有指标到全局报表模型。

        Args:
            session: 数据库会话。
            limit: 单次处理上限。

        Returns:
            处理成功的记录数。
        """
        # 1. 查找已完成深层分析但尚未转正的记录
        unpromoted = (
            session.query(GitLabCommit)
            .filter(GitLabCommit.promoted_at.is_(None))
            .filter(GitLabCommit.eloc_score > 0)  # 仅转正分析过的记录
            .limit(limit)
            .all()
        )

        if not unpromoted:
            return 0

        count = 0
        for gc in unpromoted:
            try:
                # 2. 解析主项目 ID (从关联的 GitLabProject 中获取)
                project = gc.project
                mdm_project_id = project.mdm_project_id if project else None

                # 3. 解析 OneID (UUID) - 优先通过 Email 匹配现有用户
                user = IdentityManager.get_or_create_user(
                    session,
                    source="gitlab",
                    external_id=str(gc.project_id),  # GitLab 用户 ID 有时在 commit 中不可靠，仅作为辅助
                    email=gc.author_email,
                    name=gc.author_name,
                )

                # 4. Upsert 到核心度量表 (CommitMetrics)
                metrics = session.query(CommitMetrics).filter_by(commit_sha=gc.id).first()
                if not metrics:
                    metrics = CommitMetrics(commit_sha=gc.id)

                metrics.project_id = mdm_project_id
                metrics.author_email = gc.author_email
                metrics.author_user_id = user.global_user_id if user else None
                metrics.committed_at = gc.committed_date
                metrics.raw_additions = gc.additions
                metrics.raw_deletions = gc.deletions

                # 复制插件层计算出的高级指标
                metrics.eloc_score = gc.eloc_score
                metrics.impact_score = gc.impact_score
                metrics.churn_lines = gc.churn_lines
                metrics.comment_lines = gc.comment_lines
                metrics.test_lines = gc.test_lines
                metrics.file_count = gc.file_count
                metrics.refactor_ratio = gc.refactor_ratio

                session.add(metrics)

                # 5. 标记插件记录为已转正
                gc.promoted_at = datetime.now(UTC)
                count += 1
            except Exception as e:
                logger.error(f"Failed to promote commit {gc.id}: {e}")
                continue

        session.flush()
        logger.info(f"Promoted {count} GitLab commits to rpt_commit_metrics")
        return count

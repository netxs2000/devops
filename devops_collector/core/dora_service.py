import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from devops_collector.core.algorithms import AgileMetrics
from devops_collector.models.base_models import CommitMetrics, DORAMetrics, Incident, ProjectMaster
from devops_collector.plugins.gitlab.models import GitLabDeployment, GitLabMergeRequest


logger = logging.getLogger(__name__)

class DORAService:
    """DORA 2.0 数据计算与聚合服务。

    负责跨插件采集 DORA 核心指标，并将其持久化到 MDM (rpt_dora_metrics) 表中。
    """

    @staticmethod
    def calculate_project_metrics(session: Session, project_id: int, days: int = 30) -> DORAMetrics:
        """计算指定项目的 DORA 指标并持久化。

        Args:
            session: 数据库会话。
            project_id: MDM 项目 ID。
            days: 统计的时间窗口（天）。
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=UTC)

        # 1. 部署频率 (Deployment Frequency)
        # 获取该 MDM 项目关联的所有 GitLab 项目 ID (可能存在多个代码库支撑一个项目)
        from devops_collector.plugins.gitlab.models import GitLabProject
        gitlab_project_ids = [p.id for p in session.query(GitLabProject).filter_by(mdm_project_id=project_id).all()]

        if not gitlab_project_ids:
            logger.warning(f"No GitLab projects linked to MDM Project {project_id}, skipping DORA calculation.")
            return None

        # 统计周期内成功部署到生产环境的次数
        deployments = session.query(GitLabDeployment).filter(
            GitLabDeployment.project_id.in_(gitlab_project_ids),
            GitLabDeployment.status == "success",
            GitLabDeployment.created_at >= start_dt
        ).all()

        dept_count = len(deployments)
        freq = AgileMetrics.calculate_deployment_frequency(dept_count, days)

        # 2. 变更前置时间 (Lead Time for Changes)
        # 获取统计周期内的所有已合并 MR (作为变更单元)
        mrs = session.query(GitLabMergeRequest).filter(
            GitLabMergeRequest.project_id.in_(gitlab_project_ids),
            GitLabMergeRequest.state == "merged",
            GitLabMergeRequest.merged_at >= start_dt
        ).all()

        lead_times = []
        for mr in mrs:
            # 获取该 MR 关联的所有提交时间 (利用 rpt_commit_metrics 归集后的数据)
            # 这里简化为寻找 MR 创建到合并之间的 commits
            commits = session.query(CommitMetrics).filter(
                CommitMetrics.project_id == project_id,
                CommitMetrics.committed_at >= mr.created_at,
                CommitMetrics.committed_at <= mr.merged_at
            ).all()

            commit_times = [c.committed_at for c in commits]

            # 变更前置时间 = 部署时间 - 首次提交时间
            # 寻找该 MR 对应的部署建议值（如果是滚动发布，通常取 MR 合并后的最近一次成功部署）
            # 这里简化逻辑：将合并时间作为部署完成时间的近似值 (或寻找后续部署)
            lt = AgileMetrics.calculate_dora_lead_time(commit_times, mr.merged_at)
            if lt is not None:
                lead_times.append(lt)

        lt_avg = sum(lead_times) / len(lead_times) if lead_times else 0.0

        # 3. 变更失败率 (Change Failure Rate)
        # 寻找周期内关联该项目的线上事故
        incidents = session.query(Incident).filter(
            Incident.project_id == project_id,
            Incident.occurred_at >= start_dt
        ).all()

        failure_rate = AgileMetrics.calculate_change_failure_rate(len(incidents), dept_count)

        # 4. 平均恢复时长 (MTTR)
        mttr = AgileMetrics.calculate_mttr(incidents)

        # 5. 持久化分析结果 (SCD 对齐)
        metric_record = session.query(DORAMetrics).filter_by(
            entity_id=project_id,
            entity_type="PROJECT",
            date=end_date
        ).first()

        if not metric_record:
            metric_record = DORAMetrics(
                entity_id=project_id,
                entity_type="PROJECT",
                date=end_date
            )
            session.add(metric_record)

        metric_record.deployment_count = dept_count
        metric_record.deployment_frequency = freq
        metric_record.lead_time_for_changes_avg = lt_avg
        metric_record.change_failure_rate = failure_rate
        metric_record.mttr_avg = mttr or 0.0
        metric_record.incident_count = len(incidents)

        # 综合评级
        metric_record.score_grade = DORAService._calculate_grade(freq, lt_avg)

        session.flush()
        logger.info(f"DORA 2.0 metrics calculated for Project {project_id}: Freq={freq:.2f}, LT_Avg={lt_avg:.2f}h")
        return metric_record

    @staticmethod
    def _calculate_grade(freq: float, lt: float) -> str:
        """基于 DORA 2023 标准的简单评级矩阵。"""
        # 频率：1.0+/天=Elite, 0.1+/天=High, 0.03+/天=Medium, Else=Low
        # Lead Time: <1h=Elite, <24h=High, <168h(1w)=Medium, Else=Low
        if freq >= 1.0 and lt <= 1.0:
            return "Elite"
        if freq >= 0.1 and lt <= 24.0:
            return "High"
        if freq >= 0.03 and lt <= 168.0:
            return "Medium"
        return "Low"

    @classmethod
    def aggregate_all_projects(cls, session: Session):
        """为所有活跃的 MDM 项目计算 DORA 指标。"""
        projects = session.query(ProjectMaster).filter_by(is_current=True, is_active=True).all()
        for p in projects:
            cls.calculate_project_metrics(session, p.id)
        session.commit()

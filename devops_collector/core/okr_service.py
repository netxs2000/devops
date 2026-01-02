"""DevOps Collector OKR 自动化服务类

本模块负责根据 Key Result 的配置，自动从各插件数据中提取指标并更新 OKR 进度。
实现“数据驱动战略”的闭环逻辑。
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from devops_collector.models.base_models import OKRKeyResult, OKRObjective
from devops_collector.plugins.sonarqube.models import SonarMeasure, SonarProject
from devops_collector.models import Commit, Project, Issue
logger = logging.getLogger(__name__)

class OKRService:
    """OKR 自动化更新服务。
    
    负责定期扫描 Key Result 配置，自动从各插件数据中提取指标并更新进度。
    支持 SonarQube 度量、Git 提交数及 Issue 解决数等多种动态指标。
    
    Attributes:
        session (Session): 数据库会话对象，用于持久化 OKR 进度。
        
    Example:
        service = OKRService(db_session)
        service.update_all_active_okrs()
    """

    def __init__(self, session: Session):
        """初始化 OKR 服务。
        
        Args:
            session (Session): SQLAlchemy 数据库会话。
        """
        self.session = session

    def update_all_active_okrs(self):
        """更新所有活跃状态目标的 KR 值。
        
        查询所有状态为 'active' 的 OKRObjective 关联的 Key Result，
        并逐一调用 update_key_result 进行数据同步。
        
        Returns:
            None
        """
        active_krs = self.session.query(OKRKeyResult).join(OKRObjective).filter(OKRObjective.status == 'active').all()
        logger.info(f'Starting automatic OKR update for {len(active_krs)} Key Results')
        for kr in active_krs:
            try:
                self.update_key_result(kr)
            except Exception as e:
                logger.error(f'Failed to update KR {kr.id} ({kr.title}): {e}')
        self.session.commit()

    def update_key_result(self, kr: OKRKeyResult):
        """根据配置更新单个 KR 的当前值和进度。
        
        解析 KR 的 linked_metrics_config，调用相应的私有提取方法。
        
        Args:
            kr (OKRKeyResult): 待更新的 Key Result 实体对象。
            
        Returns:
            None
        """
        config = kr.linked_metrics_config
        if not config or not isinstance(config, dict):
            return
        metric_type = config.get('type')
        new_value = None
        if metric_type == 'sonar':
            new_value = self._get_sonar_metric(config)
        elif metric_type == 'git_commit_count':
            new_value = self._get_git_commit_count(config)
        elif metric_type == 'issue_resolved_count':
            new_value = self._get_issue_resolved_count(config)
        if new_value is not None:
            kr.current_value = str(new_value)
            kr.progress = self._calculate_progress(kr)
            logger.debug(f'Updated KR {kr.id}: new_value={new_value}, progress={kr.progress}%')

    def _calculate_progress(self, kr: OKRKeyResult) -> int:
        """计算进度百分比 (0-100)。
        
        计算公式: (当前值 - 初始值) / (目标值 - 初始值)
        
        Args:
            kr (OKRKeyResult): 包含当前值、初始值和目标值的 KR 对象。
            
        Returns:
            int: 0 到 100 之间的整数进度百分比。返回 0 说明计算异常或未开始。
        """
        try:
            curr = float(kr.current_value or 0)
            target = float(kr.target_value or 0)
            initial = float(kr.initial_value or 0)
            if target == initial:
                return 100 if curr >= target else 0
            progress = int((curr - initial) / (target - initial) * 100)
            return max(0, min(100, progress))
        except (ValueError, TypeError, ZeroDivisionError):
            return 0

    def _get_sonar_metric(self, config: dict) -> Optional[float]:
        """从 SonarQube 度量值中获取最新指标。
        
        Args:
            config (dict): 配置字典，需包含 'project_key' 和 'metric_name'。
                示例: {"project_key": "xxx", "metric_name": "coverage"}
                
        Returns:
            Optional[float]: 获取到的指标数值，若未找到则返回 None。
        """
        project_key = config.get('project_key')
        metric_name = config.get('metric_name')
        if not project_key or not metric_name:
            return None
        latest_measure = self.session.query(SonarMeasure).join(SonarProject).filter(SonarProject.key == project_key).order_by(SonarMeasure.analysis_date.desc()).first()
        if latest_measure:
            value = getattr(latest_measure, metric_name, None)
            if value is not None:
                return float(value)
        return None

    def _get_git_commit_count(self, config: dict) -> int:
        """从 Git 提交记录中统计提交数。
        
        Args:
            config (dict): 配置字典，需包含 'project_id'。
                示例: {"project_id": 123}
                
        Returns:
            int: 提交总数。
        """
        project_id = config.get('project_id')
        if not project_id:
            return 0
        count = self.session.query(func.count(Commit.id)).filter_by(project_id=project_id).scalar()
        return count or 0

    def _get_issue_resolved_count(self, config: dict) -> int:
        """从 Issue 记录中统计已解决数量。
        
        Args:
            config (dict): 配置字典，需包含 'project_id'，可选 'state'。
                示例: {"project_id": 123, "state": "closed"}
                
        Returns:
            int: 已解决数量。
        """
        project_id = config.get('project_id')
        state = config.get('state', 'closed')
        if not project_id:
            return 0
        count = self.session.query(func.count(Issue.id)).filter_by(project_id=project_id, state=state).scalar()
        return count or 0
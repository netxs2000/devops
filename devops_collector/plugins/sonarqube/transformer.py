"""SonarQube 数据转换模块。

负责将 SonarQube API 返回的原始 JSON 数据转换为数据库模型对象。
遵循单一职责原则，将数据转换逻辑从 Worker 中剥离。
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from devops_collector.core.utils import safe_int, safe_float, parse_iso8601
from devops_collector.core.identity_manager import IdentityManager
from devops_collector.plugins.sonarqube.client import SonarQubeClient
from devops_collector.plugins.sonarqube.models import SonarProject, SonarMeasure, SonarIssue

logger = logging.getLogger(__name__)


class SonarDataTransformer:
    """SonarQube 数据转换器。
    
    Attributes:
        session: SQLAlchemy 数据库会话，用于查询关联数据。
        schema_version: 数据 Schema 版本。
    """
    
    def __init__(self, session):
        self.session = session

    def transform_measures_snapshot(
        self, 
        project: SonarProject, 
        measures_data: Dict, 
        gate_status: Dict = None,
        issue_dist: Dict = None,
        hotspot_dist: Dict = None
    ) -> SonarMeasure:
        """解析并创建 Sonar 指标快照模型。
        
        Args:
            project: 关联的 SonarProject 对象。
            measures_data: 原始指标数据字典。
            gate_status: 质量门禁状态字典。
            issue_dist: 问题严重分布字典。
            hotspot_dist: 安全热点分布字典。
            
        Returns:
            SonarMeasure: 填充好的指标快照对象 (尚未提交到数据库)。
        """
        gate_status = gate_status or {}
        issue_dist = issue_dist or {}
        hotspot_dist = hotspot_dist or {}
        
        bug_dist = issue_dist.get('BUG', {})
        vul_dist = issue_dist.get('VULNERABILITY', {})
        
        # 创建指标快照
        measure = SonarMeasure(
            project_id=project.id,
            analysis_date=project.last_analysis_date or datetime.now(timezone.utc),
            
            # 代码规模
            files=safe_int(measures_data.get('files')),
            lines=safe_int(measures_data.get('lines')),
            ncloc=safe_int(measures_data.get('ncloc')),
            classes=safe_int(measures_data.get('classes')),
            functions=safe_int(measures_data.get('functions')),
            statements=safe_int(measures_data.get('statements')),
            
            # 核心指标
            coverage=safe_float(measures_data.get('coverage')),
            
            # Bug 分布
            bugs=safe_int(measures_data.get('bugs')),
            bugs_blocker=bug_dist.get('BLOCKER', 0),
            bugs_critical=bug_dist.get('CRITICAL', 0),
            bugs_major=bug_dist.get('MAJOR', 0),
            bugs_minor=bug_dist.get('MINOR', 0),
            bugs_info=bug_dist.get('INFO', 0),
            
            # 漏洞分布
            vulnerabilities=safe_int(measures_data.get('vulnerabilities')),
            vulnerabilities_blocker=vul_dist.get('BLOCKER', 0),
            vulnerabilities_critical=vul_dist.get('CRITICAL', 0),
            vulnerabilities_major=vul_dist.get('MAJOR', 0),
            vulnerabilities_minor=vul_dist.get('MINOR', 0),
            vulnerabilities_info=vul_dist.get('INFO', 0),
            
            # 安全热点分布
            security_hotspots=safe_int(measures_data.get('security_hotspots')),
            security_hotspots_high=hotspot_dist.get('HIGH', 0),
            security_hotspots_medium=hotspot_dist.get('MEDIUM', 0),
            security_hotspots_low=hotspot_dist.get('LOW', 0),
            
            code_smells=safe_int(measures_data.get('code_smells')),
            comment_lines_density=safe_float(measures_data.get('comment_lines_density')),
            duplicated_lines_density=safe_float(measures_data.get('duplicated_lines_density')),
            sqale_index=safe_int(measures_data.get('sqale_index')),
            sqale_debt_ratio=safe_float(measures_data.get('sqale_debt_ratio')),
            
            # 复杂度
            complexity=safe_int(measures_data.get('complexity')),
            cognitive_complexity=safe_int(measures_data.get('cognitive_complexity')),
            
            # 评级
            reliability_rating=SonarQubeClient.rating_to_letter(
                measures_data.get('reliability_rating')
            ),
            security_rating=SonarQubeClient.rating_to_letter(
                measures_data.get('security_rating')
            ),
            sqale_rating=SonarQubeClient.rating_to_letter(
                measures_data.get('sqale_rating')
            ),
            
            # 质量门禁
            quality_gate_status=gate_status.get('status')
        )
        
        return measure

    def transform_issue(self, project: SonarProject, i_data: dict) -> SonarIssue:
        """核心解析逻辑：将原始 Sonar JSON 转换为 SonarIssue 模型。
        
        Args:
            project: 关联的 SonarProject 对象。
            i_data: 单个 Issue 的原始数据字典。
            
        Returns:
            SonarIssue: 填充好或更新后的 Issue 对象。
        """
        issue = self.session.query(SonarIssue).filter_by(
            issue_key=i_data['key']
        ).first()
        
        if not issue:
            issue = SonarIssue(
                issue_key=i_data['key'],
                project_id=project.id
            )
            # 注意：这里我们不执行 session.add，交给调用者处理，或者保持原有的隐式 add 习惯
            # 但为了明确，Transformer 通常最好只负责创建对象。
            # 鉴于原逻辑是 query -> if not create -> update，
            # 保持一致性，我们在 Transformer 里处理 DB 查询是可以接受的，
            # 只要它仍然服务于 "如何将数据映射到模型" 这个目的。
            self.session.add(issue)
        
        issue.type = i_data.get('type')
        issue.severity = i_data.get('severity')
        issue.status = i_data.get('status')
        issue.resolution = i_data.get('resolution')
        issue.rule = i_data.get('rule')
        issue.message = i_data.get('message')
        issue.component = i_data.get('component')
        issue.line = i_data.get('line')
        issue.effort = i_data.get('effort')
        issue.debt = i_data.get('debt')
        issue.assignee = i_data.get('assignee')
        if issue.assignee:
            u = IdentityManager.get_or_create_user(self.session, 'sonarqube', issue.assignee)
            issue.assignee_user_id = u.global_user_id
            
        issue.author = i_data.get('author')
        if issue.author:
            u = IdentityManager.get_or_create_user(self.session, 'sonarqube', issue.author)
            issue.author_user_id = u.global_user_id
            
        issue.raw_data = i_data
        
        # 解析时间
        issue.creation_date = parse_iso8601(i_data.get('creationDate'))
        issue.update_date = parse_iso8601(i_data.get('updateDate'))
        issue.close_date = parse_iso8601(i_data.get('closeDate'))
        
        return issue

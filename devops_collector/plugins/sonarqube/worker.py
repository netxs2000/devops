"""SonarQube 数据采集 Worker

基于 BaseWorker 实现的 SonarQube 数据同步逻辑。
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from .client import SonarQubeClient
from .models import SonarProject, SonarMeasure, SonarIssue

# 导入 GitLab Project 用于约定映射
try:
    from devops_collector.models import Project as GitLabProject
except ImportError:
    GitLabProject = None

logger = logging.getLogger(__name__)


class SonarQubeWorker(BaseWorker):
    """SonarQube 数据采集 Worker。
    
    支持同步代码质量指标和问题列表。
    
    同步数据类型:
    - 项目信息
    - 代码质量指标快照 (覆盖率、Bug、漏洞、技术债务等)
    - 问题详情 (可选，默认关闭)
    
    项目映射策略:
    - 约定映射: SonarQube Key = GitLab path_with_namespace
    """
    
    def __init__(
        self, 
        session: Session, 
        client: SonarQubeClient,
        sync_issues: bool = False
    ) -> None:
        """初始化 SonarQube Worker。
        
        Args:
            session: SQLAlchemy 数据库会话。
            client: SonarQube API 客户端。
            sync_issues: 是否同步问题详情 (默认关闭，数据量大)。
        """
        super().__init__(session, client)
        self.sync_issues = sync_issues
    
    def process_task(self, task: dict) -> None:
        """处理 SonarQube 同步任务。
        
        Args:
            task: {
                "source": "sonarqube",
                "project_key": str,  # SonarQube 项目 Key
                "job_type": "full" | "incremental",
                "sync_issues": bool  # 可选，覆盖默认设置
            }
        """
        project_key = task.get('project_key')
        job_type = task.get('job_type', 'full')
        sync_issues = task.get('sync_issues', self.sync_issues)
        
        logger.info(f"Processing SonarQube task: key={project_key}, job_type={job_type}")
        
        try:
            # 1. 同步项目信息
            project = self._sync_project(project_key)
            if not project:
                raise ValueError(f"SonarQube project {project_key} not found")
            
            project.sync_status = 'SYNCING'
            project.last_synced_at = datetime.now(timezone.utc)
            self.session.commit()
            
            # 2. 同步代码质量指标
            self._sync_measures(project)
            
            # 3. 同步问题 (可选)
            issues_count = 0
            if sync_issues:
                issues_count = self._sync_issues(project)
            
            # 4. 更新项目状态
            project.sync_status = 'COMPLETED'
            self.session.commit()
            
            self.log_success(
                f"SonarQube project {project.name} synced: "
                f"measures recorded, {issues_count} issues synced"
            )
            
        except Exception as e:
            self.session.rollback()
            
            # 更新项目状态为失败
            try:
                project = self.session.query(SonarProject).filter_by(key=project_key).first()
                if project:
                    project.sync_status = 'FAILED'
                    self.session.commit()
            except:
                pass
            
            self.log_failure(f"Failed to sync SonarQube project {project_key}", e)
            raise
    
    def _sync_project(self, key: str) -> Optional[SonarProject]:
        """同步项目信息并尝试映射到 GitLab 项目。"""
        # 从 SonarQube 获取项目信息
        p_data = self.client.get_project(key)
        if not p_data:
            return None
        
        # 查找或创建项目
        project = self.session.query(SonarProject).filter_by(key=key).first()
        if not project:
            project = SonarProject(key=key)
            self.session.add(project)
        
        project.name = p_data.get('name')
        project.qualifier = p_data.get('qualifier')
        
        # 解析最后分析时间
        if p_data.get('lastAnalysisDate'):
            try:
                project.last_analysis_date = datetime.fromisoformat(
                    p_data['lastAnalysisDate'].replace('Z', '+00:00')
                )
            except:
                pass
        
        # 约定映射: 尝试匹配 GitLab 项目
        if GitLabProject and not project.gitlab_project_id:
            gitlab_project = self.session.query(GitLabProject).filter_by(
                path_with_namespace=key
            ).first()
            if gitlab_project:
                project.gitlab_project_id = gitlab_project.id
                logger.info(f"Mapped SonarQube {key} to GitLab project {gitlab_project.id}")
        
        return project
    
    def _sync_measures(self, project: SonarProject) -> None:
        """同步代码质量指标快照。"""
        measures_data = self.client.get_measures(project.key)
        
        if not measures_data:
            logger.warning(f"No measures found for project {project.key}")
            return
        
        # 获取质量门禁状态
        gate_status = self.client.get_quality_gate_status(project.key)
        
        # 获取问题严重分布 (新增)
        issue_dist = self.client.get_issue_severity_distribution(project.key)
        bug_dist = issue_dist.get('BUG', {})
        vul_dist = issue_dist.get('VULNERABILITY', {})
        
        # 获取安全热点分布 (新增)
        hotspot_dist = self.client.get_hotspot_distribution(project.key)
        
        # 创建指标快照
        measure = SonarMeasure(
            project_id=project.id,
            analysis_date=project.last_analysis_date or datetime.now(timezone.utc),
            
            # 代码规模
            files=self._safe_int(measures_data.get('files')),
            lines=self._safe_int(measures_data.get('lines')),
            ncloc=self._safe_int(measures_data.get('ncloc')),
            classes=self._safe_int(measures_data.get('classes')),
            functions=self._safe_int(measures_data.get('functions')),
            statements=self._safe_int(measures_data.get('statements')),
            
            # 核心指标
            coverage=self._safe_float(measures_data.get('coverage')),
            
            # Bug 分布
            bugs=self._safe_int(measures_data.get('bugs')),
            bugs_blocker=bug_dist.get('BLOCKER', 0),
            bugs_critical=bug_dist.get('CRITICAL', 0),
            bugs_major=bug_dist.get('MAJOR', 0),
            bugs_minor=bug_dist.get('MINOR', 0),
            bugs_info=bug_dist.get('INFO', 0),
            
            # 漏洞分布
            vulnerabilities=self._safe_int(measures_data.get('vulnerabilities')),
            vulnerabilities_blocker=vul_dist.get('BLOCKER', 0),
            vulnerabilities_critical=vul_dist.get('CRITICAL', 0),
            vulnerabilities_major=vul_dist.get('MAJOR', 0),
            vulnerabilities_minor=vul_dist.get('MINOR', 0),
            vulnerabilities_info=vul_dist.get('INFO', 0),
            
            # 安全热点分布
            security_hotspots=self._safe_int(measures_data.get('security_hotspots')),
            security_hotspots_high=hotspot_dist.get('HIGH', 0),
            security_hotspots_medium=hotspot_dist.get('MEDIUM', 0),
            security_hotspots_low=hotspot_dist.get('LOW', 0),
            
            code_smells=self._safe_int(measures_data.get('code_smells')),
            comment_lines_density=self._safe_float(measures_data.get('comment_lines_density')),
            duplicated_lines_density=self._safe_float(measures_data.get('duplicated_lines_density')),
            sqale_index=self._safe_int(measures_data.get('sqale_index')),
            sqale_debt_ratio=self._safe_float(measures_data.get('sqale_debt_ratio')),
            
            # 复杂度
            complexity=self._safe_int(measures_data.get('complexity')),
            cognitive_complexity=self._safe_int(measures_data.get('cognitive_complexity')),
            
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
        
        self.session.add(measure)
        self.session.commit()
        
        logger.info(
            f"Recorded measures for {project.key}: "
            f"coverage={measure.coverage}%, bugs={measure.bugs}, "
            f"vulnerabilities={measure.vulnerabilities}"
        )
    
    def _sync_issues(self, project: SonarProject) -> int:
        """同步问题详情。"""
        count = 0
        page = 1
        
        while True:
            issues_data = self.client.get_issues(project.key, page=page)
            if not issues_data:
                break
            
            for i_data in issues_data:
                issue = self.session.query(SonarIssue).filter_by(
                    issue_key=i_data['key']
                ).first()
                
                if not issue:
                    issue = SonarIssue(
                        issue_key=i_data['key'],
                        project_id=project.id
                    )
                    self.session.add(issue)
                    count += 1
                
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
                issue.author = i_data.get('author')
                issue.raw_data = i_data
                
                # 解析时间
                for field in ['creationDate', 'updateDate', 'closeDate']:
                    if i_data.get(field):
                        try:
                            attr_name = {
                                'creationDate': 'creation_date',
                                'updateDate': 'update_date',
                                'closeDate': 'close_date'
                            }[field]
                            setattr(issue, attr_name, datetime.fromisoformat(
                                i_data[field].replace('Z', '+00:00')
                            ))
                        except:
                            pass
            
            page += 1
            
            # 每 500 条提交一次
            if count % 500 == 0:
                self.session.commit()
                self.log_progress("Syncing issues", count, -1)
        
        self.session.commit()
        return count
    
    def sync_all_projects(self) -> int:
        """同步所有 SonarQube 项目。
        
        Returns:
            同步的项目数量
        """
        projects = self.client.get_all_projects()
        count = 0
        
        for p_data in projects:
            try:
                task = {
                    'source': 'sonarqube',
                    'project_key': p_data['key'],
                    'job_type': 'full'
                }
                self.process_task(task)
                count += 1
            except Exception as e:
                logger.error(f"Failed to sync project {p_data['key']}: {e}")
        
        return count
    
    @staticmethod
    def _safe_int(value) -> int:
        """安全转换为整数。"""
        try:
            return int(float(value)) if value else 0
        except (ValueError, TypeError):
            return 0
    
    @staticmethod
    def _safe_float(value) -> float:
        """安全转换为浮点数。"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0


# 注册插件
PluginRegistry.register_worker('sonarqube', SonarQubeWorker)

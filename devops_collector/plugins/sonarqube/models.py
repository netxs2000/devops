"""SonarQube 数据模型

定义 SonarQube 相关的 SQLAlchemy ORM 模型。
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from devops_collector.models.base_models import Base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func, select

class SonarProject(Base):
    """SonarQube 项目模型 (sonar_projects)。
    
    存储 SonarQube 项目信息，支持与 GitLab 项目关联。

    Attributes:
        id (int): 自增主键。
        key (str): SonarQube 项目唯一标识 (e.g. com.example:my-project)。
        name (str): 项目显示名称。
        qualifier (str): 标识类型 (TRK=项目, BRC=分支, FIL=文件)。
        gitlab_project_id (int): 关联的 GitLab 项目 ID。
        last_analysis_date (datetime): 最后分析时间。
        last_synced_at (datetime): 最近同步时间。
        sync_status (str): 同步状态 (PENDING, SUCCESS, FAILED)。
        measures (List[SonarMeasure]): 关联的指标快照列表。
        issues (List[SonarIssue]): 关联的问题详情列表。
    """
    __tablename__ = 'sonar_projects'
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(500), unique=True, nullable=False)
    name = Column(String(255))
    qualifier = Column(String(10))
    gitlab_project_id = Column(Integer, ForeignKey('gitlab_projects.id'), nullable=True)
    # 使用字符串引用 'GitLabProject' 替代直接引用类对象，以解除循环导入依赖
    gitlab_project = relationship('GitLabProject', back_populates='sonar_projects')
    last_analysis_date = Column(DateTime(timezone=True))
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='PENDING')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    measures = relationship('SonarMeasure', back_populates='project', cascade='all, delete-orphan')
    issues = relationship('SonarIssue', back_populates='project', cascade='all, delete-orphan')
    latest_measure = relationship('SonarMeasure', primaryjoin='and_(SonarProject.id==SonarMeasure.project_id)', order_by='desc(SonarMeasure.analysis_date)', viewonly=True, uselist=False)

    @hybrid_property
    def bugs(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.latest_measure.bugs if self.latest_measure else 0

    @hybrid_property
    def vulnerabilities(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.latest_measure.vulnerabilities if self.latest_measure else 0

    @hybrid_property
    def coverage(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.latest_measure.coverage if self.latest_measure else 0.0

    @hybrid_property
    def quality_gate(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.latest_measure.quality_gate_status if self.latest_measure else 'UNKNOWN'

    @hybrid_property
    def is_clean(self):
        """质量门禁是否通过。"""
        return self.quality_gate == 'OK'

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<SonarProject(key='{self.key}', name='{self.name}')>"

class SonarMeasure(Base):
    """SonarQube 指标快照模型 (sonar_measures)。
    
    每次代码分析后记录一条快照，用于追踪质量趋势。

    Attributes:
        id (int): 自增主键。
        project_id (int): 关联的 Sonar 项目 ID。
        analysis_date (datetime): 分析执行时间。
        files (int): 文件数。
        lines (int): 总行数。
        ncloc (int): 有效代码行数 (Non-Comment Lines of Code)。
        coverage (float): 代码覆盖率 (%)。
        bugs (int): Bug 总数。
        vulnerabilities (int): 漏洞总数。
        security_hotspots (int): 安全热点总数。
        code_smells (int): 代码异味数。
        sqale_index (int): 技术债务 (分钟)。
        complexity (int): 圈复杂度。
        reliability_rating (str): 可靠性评级 (A-E)。
        security_rating (str): 安全性评级 (A-E)。
        sqale_rating (str): 可维护性评级 (A-E)。
        quality_gate_status (str): 质量门禁状态 (OK, WARN, ERROR)。
        project (SonarProject): 关联的项目对象。
    """
    __tablename__ = 'sonar_measures'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('sonar_projects.id'), nullable=False)
    analysis_date = Column(DateTime(timezone=True), nullable=False)
    files = Column(Integer)
    lines = Column(Integer)
    ncloc = Column(Integer)
    classes = Column(Integer)
    functions = Column(Integer)
    statements = Column(Integer)
    coverage = Column(Float)
    bugs = Column(Integer)
    bugs_blocker = Column(Integer, default=0)
    bugs_critical = Column(Integer, default=0)
    bugs_major = Column(Integer, default=0)
    bugs_minor = Column(Integer, default=0)
    bugs_info = Column(Integer, default=0)
    vulnerabilities = Column(Integer)
    vulnerabilities_blocker = Column(Integer, default=0)
    vulnerabilities_critical = Column(Integer, default=0)
    vulnerabilities_major = Column(Integer, default=0)
    vulnerabilities_minor = Column(Integer, default=0)
    vulnerabilities_info = Column(Integer, default=0)
    security_hotspots = Column(Integer)
    security_hotspots_high = Column(Integer, default=0)
    security_hotspots_medium = Column(Integer, default=0)
    security_hotspots_low = Column(Integer, default=0)
    code_smells = Column(Integer)
    comment_lines_density = Column(Float)
    duplicated_lines_density = Column(Float)
    sqale_index = Column(Integer)
    sqale_debt_ratio = Column(Float)
    complexity = Column(Integer)
    cognitive_complexity = Column(Integer)
    reliability_rating = Column(String(1))
    security_rating = Column(String(1))
    sqale_rating = Column(String(1))
    quality_gate_status = Column(String(10))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    project = relationship('SonarProject', back_populates='measures')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<SonarMeasure(project_id={self.project_id}, date='{self.analysis_date}')>"

class SonarIssue(Base):
    """SonarQube 问题详情模型 (sonar_issues)。

    Attributes:
        id (int): 自增主键。
        issue_key (str): 问题唯一标识。
        project_id (int): 关联的项目 ID。
        type (str): 类型 (BUG, VULNERABILITY, CODE_SMELL)。
        severity (str): 严重级别 (BLOCKER, CRITICAL, MAJOR, MINOR, INFO)。
        status (str): 状态 (OPEN, CONFIRMED, RESOLVED, CLOSED)。
        message (str): 问题描述。
        component (str): 文件路径。
        line (int): 行号。
        assignee_user_id (UUID): 负责人的 OneID。
        author_user_id (UUID): 作者的 OneID。
        project (SonarProject): 关联的项目对象。
    """
    __tablename__ = 'sonar_issues'
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_key = Column(String(50), unique=True, nullable=False)
    project_id = Column(Integer, ForeignKey('sonar_projects.id'), nullable=False)
    type = Column(String(20))
    severity = Column(String(20))
    status = Column(String(20))
    resolution = Column(String(20))
    rule = Column(String(200))
    message = Column(Text)
    component = Column(String(500))
    line = Column(Integer)
    effort = Column(String(20))
    debt = Column(String(20))
    creation_date = Column(DateTime(timezone=True))
    update_date = Column(DateTime(timezone=True))
    close_date = Column(DateTime(timezone=True))
    assignee = Column(String(100))
    author = Column(String(100))
    assignee_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    author_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    raw_data = Column(JSON)
    project = relationship('SonarProject', back_populates='issues')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<SonarIssue(key='{self.issue_key}', severity='{self.severity}')>"
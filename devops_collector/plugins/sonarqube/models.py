"""SonarQube 数据模型

定义 SonarQube 相关的 SQLAlchemy ORM 模型。
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# 从公共基础模型导入 Base
from devops_collector.models.base_models import Base



class SonarProject(Base):
    """SonarQube 项目模型。
    
    存储 SonarQube 项目信息，支持与 GitLab 项目关联。
    
    Attributes:
        key: SonarQube 项目唯一标识 (如 com.example:my-project)
        gitlab_project_id: 关联的 GitLab 项目 ID (约定映射)
    """
    __tablename__ = 'sonar_projects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(500), unique=True, nullable=False)  # SonarQube Project Key
    name = Column(String(255))
    qualifier = Column(String(10))  # TRK=项目, BRC=分支, FIL=文件
    
    # 关联 GitLab 项目 (约定映射: key = path_with_namespace)
    gitlab_project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    
    # 最后分析时间
    last_analysis_date = Column(DateTime(timezone=True))
    
    # 同步状态
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='PENDING')
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # 关联
    measures = relationship("SonarMeasure", back_populates="project", cascade="all, delete-orphan")
    issues = relationship("SonarIssue", back_populates="project", cascade="all, delete-orphan")


class SonarMeasure(Base):
    """SonarQube 指标快照模型。
    
    每次代码分析后记录一条快照，用于追踪质量趋势。
    
    Attributes:
        coverage: 代码覆盖率 (%)
        bugs: Bug 数量
        vulnerabilities: 漏洞数量
        code_smells: 代码异味数量
        sqale_index: 技术债务 (分钟)
        reliability_rating: 可靠性评级 (A-E)
    """
    __tablename__ = 'sonar_measures'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('sonar_projects.id'), nullable=False)
    analysis_date = Column(DateTime(timezone=True), nullable=False)
    
    # 代码规模
    files = Column(Integer)  # 文件数
    lines = Column(Integer)  # 总行数
    ncloc = Column(Integer)  # Non-Comment Lines of Code
    classes = Column(Integer) # 类数量
    functions = Column(Integer) # 方法数量
    statements = Column(Integer) # 语句数量
    
    # 代码质量核心指标
    coverage = Column(Float)                 # 代码覆盖率 (%)
    # Bug 分布
    bugs = Column(Integer)                   # Bug 数 (总计)
    bugs_blocker = Column(Integer, default=0)
    bugs_critical = Column(Integer, default=0)
    bugs_major = Column(Integer, default=0)
    bugs_minor = Column(Integer, default=0)
    bugs_info = Column(Integer, default=0)
    
    # 漏洞分布式
    vulnerabilities = Column(Integer)        # 漏洞数 (总计)
    vulnerabilities_blocker = Column(Integer, default=0)
    vulnerabilities_critical = Column(Integer, default=0)
    vulnerabilities_major = Column(Integer, default=0)
    vulnerabilities_minor = Column(Integer, default=0)
    vulnerabilities_info = Column(Integer, default=0)
    
    # 安全热点分布
    security_hotspots = Column(Integer)      # 安全热点 (总计)
    security_hotspots_high = Column(Integer, default=0)
    security_hotspots_medium = Column(Integer, default=0)
    security_hotspots_low = Column(Integer, default=0)
    
    code_smells = Column(Integer)            # 代码异味
    comment_lines_density = Column(Float)    # 注释率 (%)
    duplicated_lines_density = Column(Float) # 重复率 (%)
    sqale_index = Column(Integer)            # 技术债务 (分钟)
    sqale_debt_ratio = Column(Float)         # 技术债务率 (%)
    
    # 复杂度
    complexity = Column(Integer)             # 圈复杂度
    cognitive_complexity = Column(Integer)   # 认知复杂度
    
    # 评级 (A/B/C/D/E, 对应数值 1-5)
    reliability_rating = Column(String(1))   # 可靠性评级
    security_rating = Column(String(1))      # 安全性评级
    sqale_rating = Column(String(1))         # 可维护性评级 (技术债务评级)
    
    # 质量门禁状态
    quality_gate_status = Column(String(10)) # OK, WARN, ERROR
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    project = relationship("SonarProject", back_populates="measures")


class SonarIssue(Base):
    """SonarQube 问题详情模型 (可选，数据量较大)。
    
    存储代码质量问题的详细信息。
    默认不同步，需要在配置中显式开启。
    
    Attributes:
        issue_key: SonarQube 问题唯一标识
        type: 问题类型 (BUG, VULNERABILITY, CODE_SMELL)
        severity: 严重级别 (BLOCKER, CRITICAL, MAJOR, MINOR, INFO)
        status: 状态 (OPEN, CONFIRMED, RESOLVED, CLOSED)
    """
    __tablename__ = 'sonar_issues'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_key = Column(String(50), unique=True, nullable=False)
    project_id = Column(Integer, ForeignKey('sonar_projects.id'), nullable=False)
    
    # 问题分类
    type = Column(String(20))        # BUG, VULNERABILITY, CODE_SMELL
    severity = Column(String(20))    # BLOCKER, CRITICAL, MAJOR, MINOR, INFO
    status = Column(String(20))      # OPEN, CONFIRMED, RESOLVED, CLOSED
    resolution = Column(String(20))  # FIXED, FALSE-POSITIVE, WONTFIX
    
    # 问题详情
    rule = Column(String(200))       # 规则 Key (如 python:S1192)
    message = Column(Text)           # 问题描述
    component = Column(String(500))  # 文件路径
    line = Column(Integer)           # 行号
    effort = Column(String(20))      # 修复工时 (如 "30min")
    debt = Column(String(20))        # 技术债务 (如 "1h")
    
    # 时间戳
    creation_date = Column(DateTime(timezone=True))
    update_date = Column(DateTime(timezone=True))
    close_date = Column(DateTime(timezone=True))
    
    # 负责人
    assignee = Column(String(100))
    author = Column(String(100))
    assignee_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    author_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    
    # 原始数据
    raw_data = Column(JSON)
    
    project = relationship("SonarProject", back_populates="issues")

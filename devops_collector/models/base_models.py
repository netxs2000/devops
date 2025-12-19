"""DevOps Collector 公共模型基类

定义所有数据源共享的基础模型：
- Base: SQLAlchemy 声明式基类
- Organization: 组织架构 (公司 > 中心 > 部门 > 小组)
- User: 用户模型 (支持 GitLab 用户和虚拟用户)
- SyncLog: 同步日志

使用方式:
    from devops_collector.models.base_models import Base, Organization, User, SyncLog
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, backref
from sqlalchemy.sql import func

# SQLAlchemy 声明式基类
Base = declarative_base()


# 公共辅助类
class TimestampMixin:
    """时间戳混入类，为模型添加创建和更新时间。"""
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


class RawDataMixin:
    """原始数据混入类，存储 API 返回的完整 JSON。"""
    raw_data = Column(JSON)


class Organization(Base):
    """组织架构模型，支持多级树形结构 (公司 > 中心 > 部门 > 小组)。
    
    用于部门绩效分析和用户归属管理。
    
    Attributes:
        id: 主键
        name: 组织名称
        level: 层级类型 ('Company', 'Center', 'Department', 'Group')
        parent_id: 父节点 ID，用于构建树形结构
        users: 关联的用户列表
        projects: 关联的项目列表（由 GitLab 插件定义）
    """
    __tablename__ = 'organizations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    level = Column(String(20))  # Company, Center, Department, Group
    parent_id = Column(Integer, ForeignKey('organizations.id'))
    
    # 自关联关系
    children = relationship("Organization", backref=backref('parent', remote_side=[id]))
    
    # 关联用户（双向关系）
    # 注意：这里不直接定义 relationship，而是在各插件 of User 模型中通过 back_populates 建立
    # 这样可以避免循环导入问题
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


class User(Base):
    """用户模型，全局唯一身份标识。
    
    聚合来自各个系统（GitLab, Jira, ZenTao等）的人员信息，作为效能分析的核心维度。
    
    Attributes:
        id: 自增主键。
        username: 内部系统唯一用户名。
        name: 用户真实姓名或显示名称。
        email: 唯一邮箱，用于跨系统自动匹配用户身份。
        state: 用户状态 (active, blocked)。
        department: 所属部门名称。
        organization_id: 关联的组织架构 ID。
        raw_data: 原始 JSON 备份。
        created_at: 记录创建时间。
        updated_at: 记录更新时间。
        identities: 该用户在各外部系统中的身份映射列表。
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True) # 内部唯一用户名
    name = Column(String(200))
    email = Column(String(200), unique=True)    # 唯一邮箱，用于自动匹配
    
    state = Column(String(20)) # active, blocked
    department = Column(String(100))
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # 关联
    identities = relationship("IdentityMapping", back_populates="user", cascade="all, delete-orphan")


class IdentityMapping(Base):
    """身份映射表，记录不同系统的账号归属。
    
    Attributes:
        id: 自增主键。
        user_id: 关联的系统统一用户 ID。
        source: 外部系统来源 (jira, zentao, gitlab, jenkins, sonarqube)。
        external_id: 外部系统中的账号名或唯一标识。
        external_name: 外部系统的显示名。
        email: 外部账号对应的邮箱（辅助匹配）。
        user: 关联的 User 对象。
        created_at: 记录创建时间。
    """
    __tablename__ = 'identity_mappings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    source = Column(String(50), nullable=False)      # jira, zentao, gitlab, jenkins, sonarqube
    external_id = Column(String(200), nullable=False) # 外部系统的账号名或 ID
    external_name = Column(String(200))              # 外部系统的显示名
    email = Column(String(200))                       # 该账号对应的邮箱（辅助匹配）
    
    user = relationship("User", back_populates="identities")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        UniqueConstraint('source', 'external_id', name='idx_source_external'),
    )


class SyncLog(Base):
    """同步日志模型，记录每次同步任务的执行结果。
    
    Attributes:
        id: 自增主键。
        source: 数据源来源。
        project_id: 关联的项目 ID。
        project_key: SonarQube 等系统的项目唯一键。
        status: 同步结果状态 (SUCCESS, FAILED)。
        message: 详细的同步消息或错误堆栈。
        duration_seconds: 本次同步任务耗时（秒）。
        records_synced: 本次成功同步的数据记录数。
        timestamp: 日志记录时间。
    """
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(20), default='gitlab')  # gitlab, sonarqube
    project_id = Column(Integer)  # 通用项目 ID
    project_key = Column(String(200))  # SonarQube 项目 Key
    status = Column(String(20))  # SUCCESS, FAILED
    message = Column(Text)
    duration_seconds = Column(Integer)  # 同步耗时
    records_synced = Column(Integer)  # 同步记录数
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Product(Base):
    """全局产品模型，支持“产品线 -> 产品”的层级结构。
    
    用于在业务层面聚合技术项目和负责人，是多项目协作和成本分析的基础。
    
    Attributes:
        id: 自增主键。
        name: 产品或产品线名称。
        description: 详细描述。
        level: 层级分类 (Line: 产品线, Product: 产品)。
        parent_id: 父节点 ID。
        product_line_name: 冗余存储的产品线名称（用于快速查询）。
        organization_id: 归属的组织架构 ID。
        project_id: 该产品关联的技术项目起始 ID (具体业务含义见插件)。
        external_epic_id: 外部需求系统的 Epic ID。
        external_goal_id: 外部需求系统的 Goal ID。
        source_system: 外部系统来源。
        product_manager_id: 产品经理 User ID。
        dev_manager_id: 开发经理 User ID。
        test_manager_id: 测试经理 User ID。
        release_manager_id: 交付经理 User ID。
        budget_amount: 产品预算金额。
        business_value_score: 业务价值评分。
        raw_data: 原始 JSON 备份。
    """
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 层级结构
    level = Column(String(20)) # Line (产品线), Product (产品)
    parent_id = Column(Integer, ForeignKey('products.id'))
    product_line_name = Column(String(200)) # 冗余字段方便查询
    
    # 归属中心
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    
    # 关联的技术项目 ID (由具体插件定义意义)
    project_id = Column(Integer)
    
    # 外部关联 (Jira/ZenTao)
    external_epic_id = Column(String(100))  # 关联外部 Epic ID
    external_goal_id = Column(String(100))  # 关联外部 Goal/Objective ID
    source_system = Column(String(50))      # zentao, jira
    
    # 角色负责人 (关联到全局 User)
    product_manager_id = Column(Integer, ForeignKey('users.id'))
    dev_manager_id = Column(Integer, ForeignKey('users.id'))
    test_manager_id = Column(Integer, ForeignKey('users.id'))
    release_manager_id = Column(Integer, ForeignKey('users.id'))
    
    # 关系
    children = relationship("Product", backref=backref('parent', remote_side=[id]))
    organization = relationship("Organization")
    
    product_manager = relationship("User", foreign_keys=[product_manager_id])
    dev_manager = relationship("User", foreign_keys=[dev_manager_id])
    test_manager = relationship("User", foreign_keys=[test_manager_id])
    release_manager = relationship("User", foreign_keys=[release_manager_id])
    
    # 关联 OKR 目标
    objectives = relationship("OKRObjective", back_populates="product")
    
    # 财务与业务指标：支持 ROI 与波士顿矩阵分析
    budget_amount = Column(func.float)       # 预算金额
    business_value_score = Column(Integer)   # 业务价值评分 (1-100)
    
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


class OKRObjective(Base, TimestampMixin):
    """OKR 目标模型 (Objective)。
    
    代表战略高度的业务目标，支持多级树形结构进行战略分解（公司 > 中心 > 部门）。
    
    Attributes:
        id: 主键。
        title: 目标标题。
        description: 目标详细描述。
        owner_id: 责任人 ID。
        organization_id: 归属组织 ID（中心/部门）。
        period: 周期（如 2024-Q4）。
        status: 状态（draft, active, achieved, closed）。
        product_id: 关联的产品 ID。
        parent_id: 父目标 ID。
    """
    __tablename__ = 'okr_objectives'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # 责任人与归属
    owner_id = Column(Integer, ForeignKey('users.id'))
    organization_id = Column(Integer, ForeignKey('organizations.id'))

    # 周期与状态
    period = Column(String(50))
    status = Column(String(20), default='draft')

    # 关系与层级
    product_id = Column(Integer, ForeignKey('products.id'))
    parent_id = Column(Integer, ForeignKey('okr_objectives.id'))

    # 关系映射
    product = relationship("Product", back_populates="objectives")
    owner = relationship("User")
    organization = relationship("Organization")
    children = relationship("OKRObjective", backref=backref('parent', remote_side=[id]))
    key_results = relationship("OKRKeyResult", back_populates="objective", cascade="all, delete-orphan")


class OKRKeyResult(Base, TimestampMixin):
    """OKR 关键结果模型 (Key Result)。
    
    定义衡量目标完成情况的具体量化指标。
    
    Attributes:
        id: 主键。
        objective_id: 关联的目标 ID。
        title: KR 标题。
        target_value: 目标达成值。
        current_value: 当前实际值。
        metric_unit: 计量单位（%，天，个等）。
        linked_metrics_config: 关联的自动化采集指标配置（JSON）。
        progress: 进度百分比 (0-100)。
    """
    __tablename__ = 'okr_key_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    objective_id = Column(Integer, ForeignKey('okr_objectives.id'), nullable=False)

    title = Column(String(500), nullable=False)

    # 度量值
    initial_value = Column(String(100))
    target_value = Column(String(100))
    current_value = Column(String(100))
    metric_unit = Column(String(50))

    # 自动关联配置
    linked_metrics_config = Column(JSON)
    progress = Column(Integer, default=0)

    # 关系映射
    objective = relationship("OKRObjective", back_populates="key_results")


class TraceabilityLink(Base, TimestampMixin):
    """通用链路追溯映射表。
    
    支持在任意两个 DevOps 对象之间建立链接（如：Jira Issue <-> GitLab MR）。
    
    Attributes:
        id: 主键。
        source_system: 源系统 (jira, zentao, gitlab, jenkins)。
        source_type: 源对象类型 (issue, story, bug, task)。
        source_id: 源对象外部 ID 或系统内 ID。
        target_system: 目标系统 (gitlab, jenkins, sonarqube)。
        target_type: 目标对象类型 (commit, mr, build, pipeline)。
        target_id: 目标对象外部 ID 或系统内 ID。
        link_type: 链路类型 (fixes, relates_to, derived_from, deploys)。
        raw_data: 存储来源系统提供的原始映射元数据。
    """
    __tablename__ = 'traceability_links'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 源对象
    source_system = Column(String(50), nullable=False) # jira, zentao, gitlab, jenkins
    source_type = Column(String(50), nullable=False)   # issue, story, bug, task
    source_id = Column(String(100), nullable=False)     # 外部 ID 或系统内 ID
    
    # 目标对象
    target_system = Column(String(50), nullable=False) # gitlab, jenkins, sonarqube
    target_type = Column(String(50), nullable=False)   # commit, mr, build, pipeline
    target_id = Column(String(100), nullable=False)     # 外部 ID 或系统内 ID
    
    # 链路属性
    link_type = Column(String(50)) # fixes, relates_to, derived_from, deploys
    raw_data = Column(JSON)        # 存储来源系统提供的原始映射元数据


class TestExecutionSummary(Base, TimestampMixin):
    """测试执行汇总记录模型。
    
    聚合单次构建或测试任务的全量结果，支持测试金字塔分层分析。
    
    Attributes:
        id: 自增主键。
        project_id: 关联的 GitLab 项目 ID。
        build_id: 关联的 Jenkins Build ID 或外部 Job ID。
        test_level: 测试层级 (Unit, API, UI, Integration, Performance)。
        test_tool: 使用的测试工具 (pytest, jmeter, selenium 等)。
        total_cases: 总测试用例数。
        passed_count: 通过数。
        failed_count: 失败数。
        skipped_count: 跳过数。
        pass_rate: 通过率百分比。
        duration_ms: 执行总耗时 (毫秒)。
        raw_data: 原始 JSON 备份。
    """
    __tablename__ = 'test_execution_summaries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer)  # 关联 GitLab 项目 ID
    build_id = Column(String(100)) # 关联 Jenkins Build ID 或外部 Job ID
    
    # 核心维度：Unit, API, UI, Integration, Performance
    test_level = Column(String(50), nullable=False) 
    test_tool = Column(String(50))  # pytest, jmeter, selenium, etc.
    
    # 度量指标
    total_cases = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    pass_rate = Column(func.float) # 计算字段
    duration_ms = Column(BigInteger) # 执行耗时
    
    raw_data = Column(JSON)


class PerformanceRecord(Base, TimestampMixin):
    """性能基准测试记录模型。
    
    用于监控核心路径在全生命周期中的性能抖动。
    
    Attributes:
        id: 自增主键。
        project_id: 关联的项目 ID。
        build_id: 关联的构建 ID。
        scenario_name: 压测场景或接口名称。
        avg_latency: 平均耗时 (ms)。
        p99_latency: P99 耗时 (ms)。
        throughput: 吞吐量 (TPS/RPS)。
        error_rate: 错误率 (%)。
        concurrency: 并发用户数。
        raw_data: 原始 JSON。
    """
    __tablename__ = 'performance_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer)
    build_id = Column(String(100))
    
    scenario_name = Column(String(200), nullable=False) # 压测场景或接口名
    
    # 核心性能指标
    avg_latency = Column(func.float) # 平均耗时 (ms)
    p99_latency = Column(func.float) # P99 耗时 (ms)
    throughput = Column(func.float)  # 吞吐量 (TPS/RPS)
    error_rate = Column(func.float)  # 错误率 (%)
    
    concurrency = Column(Integer)    # 并发数
    
    raw_data = Column(JSON)


class Incident(Base, TimestampMixin):
    """运维事故/故障记录模型。
    
    用于计算 MTTR (平均恢复时间) 和变更失败率。
    
    Attributes:
        id: 自增主键。
        external_id: 外部系统 ID (如 JIRA-999)。
        source_system: 来源系统 (jira, zentao, pagerduty, prometheus)。
        title: 事故标题。
        description: 事故详细描述。
        severity: 严重等级 (P0, P1, P2, P3)。
        status: 处理状态 (investigating, resolved, closed)。
        occurred_at: 发现时间。
        resolved_at: 恢复时间。
        mttr_seconds: 恢复耗时 (秒)。
        project_id: 关联的 GitLab 项目 ID。
        related_deployment_id: 关联的可能导致故障的部署 ID。
        related_change_sha: 关联的可能导致故障的提交 SHA。
        root_cause_type: 根因分类 (CodeBug, Infra 等)。
        impact_scope: 影响范围描述。
        raw_data: 原始 JSON 数据。
    """
    __tablename__ = 'incidents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), unique=True) # 外部系统 ID (如 JIRA-999)
    source_system = Column(String(50))             # jira, zentao, pagerduty, prometheus
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    # 核心状态与等级
    severity = Column(String(20)) # P0(Urgent), P1(High), P2, P3
    status = Column(String(20))   # investigating, resolved, closed
    
    # 时间线指标 (MTTR 核心)
    occurred_at = Column(DateTime(timezone=True)) # 事故发生/发现时间
    resolved_at = Column(DateTime(timezone=True)) # 服务恢复时间
    mttr_seconds = Column(Integer)                # 恢复耗时 (resolved - occurred)
    
    # 链路追溯：定责与影响分析
    project_id = Column(Integer)                  # 关联 GitLab 项目 ID
    related_deployment_id = Column(Integer)       # 关联导致故障的部署 ID
    related_change_sha = Column(String(100))      # 关联导致故障的提交 SHA
    
    # 根因分析
    root_cause_type = Column(String(50)) # CodeBug, ConfigError, Infra, HumanError
    impact_scope = Column(String(200))   # 影响范围 (如: 全量用户, 华东区)
    
    raw_data = Column(JSON)


class ResourceCost(Base, TimestampMixin):
    """资源与成本统计模型。
    
    记录基础设施（云服务、服务器）、人力分摊及授权成本，支持 FinOps 分析。
    
    Attributes:
        id: 自增主键。
        project_id: 关联的项目 ID。
        product_id: 关联的产品 ID。
        organization_id: 关联的组织 ID。
        period: 统计周期 (如 2025-01)。
        cost_type: 成本类型 (Infrastructure, HumanLabor 等)。
        cost_item: 具体成本项名。
        amount: 金额。
        currency: 币种 (默认 CNY)。
        source_system: 成本数据来源系统。
        description: 备注说明。
        raw_data: 原始数据备份。
    """
    __tablename__ = 'resource_costs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 归属维度（多选一或组合）
    project_id = Column(Integer)      # 关联 GitLab 项目 ID
    product_id = Column(Integer)      # 关联全局产品 ID
    organization_id = Column(Integer)  # 关联组织架构 ID (部门/中心)
    
    # 时间维度
    period = Column(String(50), nullable=False) # 周期：2025-01, 2025-Q1, 2025-Annual
    
    # 成本分类
    cost_type = Column(String(50))   # 分类：Infrastructure(基建), HumanLabor(人力), Licensing(授权), Cloud(云服务)
    cost_item = Column(String(100))  # 具体项目：AWS-EC2, SonarQube-License, DeveloperSalaray
    
    # 金额指标
    amount = Column(func.float, nullable=False)
    currency = Column(String(10), default='CNY') # 币种
    
    # 数据来源
    source_system = Column(String(50)) # 来源：aws_billing, internal_hr, manual_entry
    
    description = Column(Text)
    raw_data = Column(JSON)


class UserActivityProfile(Base, TimestampMixin):
    """用户行为特征画像模型。
    
    记录开发者在一段时间内的协作行为特征与平均效能指标，用于团队效能辅导。
    
    Attributes:
        id: 自增主键。
        user_id: 关联的用户 ID。
        period: 统计周期。
        avg_review_turnaround: 平均评审响应时长 (秒)。
        review_participation_rate: 评审参与率。
        context_switch_rate: 任务切换频率。
        contribution_diversity: 贡献多样性得分。
        top_languages: 主要编程语言分布 (JSON)。
        off_hours_activity_ratio: 非工作时间活跃占比。
        weekend_activity_count: 周末活跃天数。
        avg_lint_errors_per_kloc: 千行代码平均 Lint 错误。
        code_review_acceptance_rate: 评审一次性通过率。
        user: 关联的 User 对象。
        raw_data: 原始数据。
    """
    __tablename__ = 'user_activity_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    period = Column(String(50), nullable=False) # 统计周期：2025-01, 2025-Q1
    
    # 协作深度指标
    avg_review_turnaround = Column(func.float) # 平均评审响应时长 (秒)
    review_participation_rate = Column(func.float) # 评审参与率
    
    # 认知负担指标
    context_switch_rate = Column(func.float)    # 任务切换频率 (平均每天处理的项目或仓库数)
    contribution_diversity = Column(func.float) # 贡献多样性 (跨项目分布得分)
    
    # 技术特征
    top_languages = Column(JSON)  # 主要编程语言分布
    
    # 行为健康指标 (加班与负荷)
    off_hours_activity_ratio = Column(func.float) # 非工作时间活动占比 (如 20:00 - 08:00)
    weekend_activity_count = Column(Integer)      # 周末活跃天数
    
    # 代码规范与质量遵循度
    avg_lint_errors_per_kloc = Column(func.float) # 每千行代码平均 Lint 错误数
    code_review_acceptance_rate = Column(func.float) # 评审通过率 (无需返工直接合并的比例)
    
    user = relationship("User")
    raw_data = Column(JSON)





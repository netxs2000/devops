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
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, UniqueConstraint, Float, BigInteger, Index
from sqlalchemy.orm import declarative_base, relationship, backref
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB


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


class RawDataStaging(Base):
    """原始数据落盘表 (Staging Layer)。
    
    用于存储未经转换的原始 API 响应内容。支持按需重放、审计以及故障排查。
    配合生命周期管理策略，可定期清理旧数据。
    
    Attributes:
        id: 自增主键。
        source: 数据源来源 (gitlab, sonarqube, jenkins 等)。
        entity_type: 实体类型 (merge_request, project, issue, build 等)。
        external_id: 外部系统的唯一标识 (如 MR 的 IID 或项目 ID)。
        payload: 原始 JSON 响应内容。
        collected_at: 采集时间，用于生命周期管理。
    """
    __tablename__ = 'raw_data_staging'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    external_id = Column(String(100), nullable=False, index=True)
    
    payload = Column(JSON, nullable=False)
    schema_version = Column(String(20), default="1.0", index=True) # 记录采集时的 Schema 版本
    collected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    __table_args__ = (
        UniqueConstraint('source', 'entity_type', 'external_id', name='idx_source_entity_extid'),
    )


class Organization(Base):
    """组织架构主数据 (mdm_organizations)。
    
    建立全集团的汇报线与成本中心映射，支持指标按部门层级汇总。
    采用 SCD Type 2 (保留历史版本)。
    
    Attributes:
        org_id: 组织唯一编码 (Global ID, e.g., ORG_FIN_001).
        org_name: 组织/部门名称.
        parent_org_id: 父级组织 ID.
        org_level: 组织层级 (1-集团, 2-事业部, 3-部门).
        manager_user_id: 部门负责人 ID (关联 mdm_identities).
        cost_center: 财务成本中心代码.
        is_deleted: 逻辑删除标记.
    """
    __tablename__ = 'mdm_organizations'
    
    org_id = Column(String(100), primary_key=True)
    org_name = Column(String(200), nullable=False)
    parent_org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    
    org_level = Column(Integer)  # 1-Group, 2-BU, 3-Dept
    
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    
    cost_center = Column(String(100)) # 财务成本中心代码
    is_deleted = Column(Boolean, default=False)
    
    # 自关联关系
    children = relationship("Organization", backref=backref('parent', remote_side=[org_id]))
    
    # 关联服务
    services = relationship("Service", back_populates="organization")

    # 关联用户（双向关系）
    # 注意：这里不直接定义 relationship，而是在各插件 of User 模型中通过 back_populates 建立
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


class Location(Base):
    """地理位置主数据 (mdm_location)。
    
    为支持省、市、区县三级层级结构，省级主数据表通常采用统一地址代码表结构（适配 GB/T 2260 国标）。
    通过字段关联实现层级管理，支持地域维度的数据隔离和质量分析。
    
    Attributes:
        location_id: 国家标准行政区划代码 (唯一标识)，如 '110105' (朝阳区)。
        location_name: 全称（省/市/区县名称），如 '北京市朝阳区'。
        location_type: 层级类型（province/city/district）。
        parent_id: 父级行政区划代码（省级为NULL）。
        short_name: 简称，如 '朝阳'。
        region: 经济大区（如华东/华南/华北），用于区域性分析。
        is_active: 是否启用（控制失效行政区）。
        manager_user_id: 区域负责人ID（关联 mdm_identities），用于定向推送通知。
    """
    __tablename__ = 'mdm_location'
    
    location_id = Column(String(6), primary_key=True)  # 国家标准行政区划代码
    location_name = Column(String(50), nullable=False)  # 全称（省/市/区县名称）
    location_type = Column(String(20), nullable=False)  # 层级类型: province/city/district
    parent_id = Column(String(6), ForeignKey('mdm_location.location_id'))  # 父级行政区划代码（省级为NULL）
    short_name = Column(String(20), nullable=False)  # 简称
    region = Column(String(10), nullable=False)  # 经济大区（如华东/华南/华北）
    is_active = Column(Boolean, default=True)  # 是否启用（控制失效行政区）
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))  # 区域负责人ID
    
    # 自关联关系：支持省 -> 市 -> 区县层级
    children = relationship("Location", backref=backref('parent', remote_side=[location_id]))
    
    # 关联区域负责人
    manager = relationship("User", foreign_keys=[manager_user_id])
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (
        Index('idx_location_type', location_type),
        Index('idx_location_parent', parent_id),
    )


class User(Base):
    """人员主数据 (mdm_identities)。
    
    全局唯一标识，集团级唯一身份 ID (OneID).
    
    Attributes:
        global_user_id: 全局唯一标识 (UUID).
        employee_id: 集团 HR 系统工号 (核心锚点).
        full_name: 法律姓名.
        primary_email: 集团官方办公邮箱.
        identity_map: 多系统账号映射关系 (JSONB).
        match_confidence: 算法匹配置信度 (0.0-1.0).
        is_survivor: 是否为当前生效的“生存者”黄金记录.
        is_active: 账号状态 (在职/离职).
        updated_at: 最后更新时间.
        source_system: 标记该“生存者记录”的主来源系统.
        sync_version: 乐观锁版本号.
    """
    __tablename__ = 'mdm_identities'
    
    global_user_id = Column(UUID(as_uuid=True), primary_key=True, default=func.uuid_generate_v4())
    employee_id = Column(String(50), unique=True) # Unique HR ID
    full_name = Column(String(200), nullable=False)
    primary_email = Column(String(200), unique=True)
    
    identity_map = Column(JSONB) # {"gitlab": 12, "jira": "J_01"}
    
    match_confidence = Column(Float)
    is_survivor = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    source_system = Column(String(50)) # e.g., HRMS
    sync_version = Column(BigInteger, default=1)
    


    # 组织与地域属性 (用于数据隔离与权限控制)
    department_id = Column(UUID(as_uuid=True), ForeignKey('mdm_organizations.global_org_id'))  # 所属部门/组织
    location_id = Column(String(6), ForeignKey('mdm_location.location_id'))  # 所属地理位置（关联 mdm_location）
    
    # 关联关系
    department = relationship("Organization", foreign_keys=[department_id])
    location = relationship("Location", foreign_keys=[location_id])
    # identities = relationship("IdentityMapping", back_populates="user", cascade="all, delete-orphan") # Deprecated or kept for compat?
    # Keeping IdentityMapping model for now but might need adjustment.
    
    __table_args__ = (
        Index('idx_identity_map', identity_map, postgresql_using='gin'),
    )



class LaborRateConfig(Base, TimestampMixin):
    """人工费率配置模型 (Labor Rate Configuration)。

    用于定义不同岗位级别、不同区域或不同组织的“标准人天成本 (Blended Rate)”。
    通过标准费率而非真实工资进行核算，在保护员工隐私的同时符合财务预算模型。

    Attributes:
        id: 自增内部主键。
        job_title_level: 岗位序列与级别 (与 User.job_title_level 对应，如 P7, Senior)。
        organization_id: 关联的组织 ID (可选)。支持不同部门或地域设置不同的核算费率。
        daily_rate: 标准人天成本金额。
        hourly_rate: 标准人时成本金额 (通常为 daily_rate / 8)。
        currency: 币种代码 (如 CNY, USD)。
        effective_date: 费率生效时间。
        is_active: 是否启用该费率配置。
        organization: 关联的 Organization 对对象。
    """
    __tablename__ = 'labor_rate_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_title_level = Column(String(100), nullable=False, index=True)
    organization_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), nullable=True)
    
    daily_rate = Column(Float, nullable=False)
    hourly_rate = Column(Float)
    currency = Column(String(10), default='CNY')
    
    effective_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    organization = relationship("Organization")


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
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=False)
    
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
    # 归属中心
    organization_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    finance_code = Column(String(100)) # 关联财务系统的预算科目或项目代码
    
    # 关联的技术项目 ID (由具体插件定义意义)
    project_id = Column(Integer)
    
    # 外部关联 (Jira/ZenTao)
    external_epic_id = Column(String(100))  # 关联外部 Epic ID
    external_goal_id = Column(String(100))  # 关联外部 Goal/Objective ID
    source_system = Column(String(50))      # zentao, jira
    
    # 角色负责人 (关联到全局 User)
    # 角色负责人 (关联到全局 User)
    product_manager_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    dev_manager_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    test_manager_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    release_manager_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    
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
    budget_amount = Column(Float)            # 预算金额
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
    # 责任人与归属
    owner_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    organization_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))

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


class Service(Base, TimestampMixin):
    """服务目录模型 (Service Catalog)。
    
    用于在逻辑层面定义业务服务，一个服务可能对应多个技术项目(Repositories)。
    跨越 DevOps L4 的核心元数据。
    
    Attributes:
        id: 自增主键。
        name: 服务名称。
        tier: 服务等级 (P0: 核心, P1: 重要, P2: 一般, P3: 次要)。
        description: 服务描述。
        organization_id: 归属的组织/团队 ID。
        product_id: 关联的产品 ID。
        raw_data: 原始 JSON 备份。
    """
    __tablename__ = 'services'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    tier = Column(String(20)) # P0, P1, P2, P3
    description = Column(Text)
    
    organization_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    
    raw_data = Column(JSON)
    
    # 关系映射
    organization = relationship("Organization", back_populates="services")
    product = relationship("Product")
    slos = relationship("SLO", back_populates="service", cascade="all, delete-orphan")
    projects = relationship("ServiceProjectMapping", back_populates="service", cascade="all, delete-orphan")


class ServiceProjectMapping(Base, TimestampMixin):
    """服务与技术项目映射表。
    
    解决一个逻辑服务对应多个代码仓库/项目的问题。
    """
    __tablename__ = 'service_project_mappings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    
    # 关联技术项目 (跨插件支持)
    source = Column(String(50), default='gitlab') # gitlab, etc.
    project_id = Column(Integer, nullable=False)   # 对应插件系统中的项目 ID
    
    service = relationship("Service", back_populates="projects")


class SLO(Base, TimestampMixin):
    """服务等级目标模型 (SLO)。
    
    定义服务的可靠性承诺，衡量服务是否达到预期水平。
    
    Attributes:
        id: 自增主键。
        service_id: 关联的服务 ID。
        name: SLO 名称 (如 Availability, Latency P99)。
        indicator_type: 指标类型 (Availability, Latency, ErrorRate, Throughput)。
        target_value: 目标达成值 (如 99.9, 200)。
        metric_unit: 计量单位 (%, ms, ops/s)。
        time_window: 统计时间窗口 (7d, 28d, 30d)。
        description: 指标定义描述。
    """
    __tablename__ = 'slos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    
    name = Column(String(200), nullable=False)
    indicator_type = Column(String(50)) # Availability, Latency, ErrorRate, Throughput
    
    target_value = Column(Float, nullable=False)
    metric_unit = Column(String(20))    # %, ms, req/s
    time_window = Column(String(20))    # 7d, 28d, 30d
    
    description = Column(Text)
    
    # 关系映射
    service = relationship("Service", back_populates="slos")


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
    pass_rate = Column(Float) # 计算字段
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
    avg_latency = Column(Float) # 平均耗时 (ms)
    p99_latency = Column(Float) # P99 耗时 (ms)
    throughput = Column(Float)  # 吞吐量 (TPS/RPS)
    error_rate = Column(Float)  # 错误率 (%)
    
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


class CostCode(Base, TimestampMixin):
    """成本分解结构模型 (Cost Breakdown Structure - CBS Tree)。

    用于建立独立于行政组织的财务核算体系，作为项目投入和预算控制的核心维度。
    支持无限层级的科目分解 (如：1000 技术投入 -> 1001 云服务 -> 1001.01 计算节点)。

    Attributes:
        id: 自增内部主键。
        code: 财务科目编码 (唯一，如 1002.01.03)。
        name: 科目显示名称 (如 云服务器存储费)。
        description: 该科目的具体适用范围和核算规则说明。
        parent_id: 父级科目 ID，用于构建树形层级。
        category: 成本大类 (如 Labor, Cloud, License, Infrastructure)。
        default_capex_opex: 默认支出性质建议 (CAPEX 代表资本化，OPEX 代表费用化)。
        is_active: 状态标记，停用的科目不再参与新的成本关联。
        costs: 关联的 ResourceCost 列表。
    """
    __tablename__ = 'cost_codes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False) # 财务编码映射
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 树形结构
    parent_id = Column(Integer, ForeignKey('cost_codes.id'))
    children = relationship("CostCode", backref=backref('parent', remote_side=[id]))
    
    # 财务属性
    category = Column(String(50))           # Labor, Cloud, License, Infrastructure, etc.
    default_capex_opex = Column(String(20)) # CAPEX, OPEX
    is_active = Column(Boolean, default=True)
    
    costs = relationship("ResourceCost", back_populates="cost_code")


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
    organization_id = Column(String(100))  # 关联组织架构 ID (部门/中心)
    
    # 时间维度
    period = Column(String(50), nullable=False) # 周期：2025-01, 2025-Q1, 2025-Annual
    
    # 成本分类
    cost_type = Column(String(50))   # 分类：Infrastructure(基建), HumanLabor(人力), Licensing(授权), Cloud(云服务)
    cost_item = Column(String(100))  # 具体项目：AWS-EC2, SonarQube-License, DeveloperSalaray
    
    # 财务关联核心
    cost_code_id = Column(Integer, ForeignKey('cost_codes.id'))
    cost_code = relationship("CostCode", back_populates="costs")
    
    purchase_contract_id = Column(Integer, ForeignKey('purchase_contracts.id'))
    purchase_contract = relationship("PurchaseContract", back_populates="costs")
    
    # 冗余字段方便快速查询
    vendor_name = Column(String(200))
    
    # 指标
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='CNY')   # 币种
    
    # 财务合规字段
    capex_opex_flag = Column(String(20))           # CAPEX (资本化), OPEX (费用化)
    finance_category = Column(String(100))         # 财务科目分类
    is_locked = Column(Boolean, default=False)     # 关账状态：True 则禁止修改，保护审计数据
    accounting_date = Column(DateTime(timezone=True)) # 账务发生日期
    
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
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=False)
    period = Column(String(50), nullable=False) # 统计周期：2025-01, 2025-Q1
    
    # 协作深度指标
    avg_review_turnaround = Column(Float) # 平均评审响应时长 (秒)
    review_participation_rate = Column(Float) # 评审参与率
    
    # 认知负担指标
    context_switch_rate = Column(Float)    # 任务切换频率 (平均每天处理的项目或仓库数)
    contribution_diversity = Column(Float) # 贡献多样性 (跨项目分布得分)
    
    # 技术特征
    top_languages = Column(JSON)  # 主要编程语言分布
    
    # 行为健康指标 (加班与负荷)
    off_hours_activity_ratio = Column(Float) # 非工作时间活动占比 (如 20:00 - 08:00)
    weekend_activity_count = Column(Integer)      # 周末活跃天数
    
    # 代码规范与质量遵循度
    avg_lint_errors_per_kloc = Column(Float) # 每千行代码平均 Lint 错误数
    code_review_acceptance_rate = Column(Float) # 评审通过率 (无需返工直接合并的比例)
    
    user = relationship("User")
    raw_data = Column(JSON)


class RevenueContract(Base, TimestampMixin):
    """收入合同模型 (Revenue Contract)。

    记录业务端签署的产生外部收入的合同，并将其回款条件与研发项目的里程碑进行联动。
    有助于实现“基于价值交付的收入确认”和“项目 ROI 分析”。

    Attributes:
        id: 自增内部主键。
        contract_no: 外部合同唯一编号。
        title: 合同名称或项目名称简述。
        client_name: 客户或集成商名称。
        total_value: 合同含税总金额。
        currency: 币种 (默认 CNY)。
        sign_date: 合同正式签署日期。
        start_date: 服务期/履行起始日期。
        end_date: 服务期/履行截止日期。
        product_id: 关联的内部产品 ID。
        organization_id: 负责交付的内部组织 ID。
        status: 合同生命周期状态 (Active, Finished, Suspended)。
        raw_data: 存储来自外部合同系统的原始 JSON 镜像。
        product: 关联的 Product 模型。
        organization: 关联的 Organization 模型。
        payment_nodes: 关联的分阶段收款节点集合。
    """
    __tablename__ = 'revenue_contracts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_no = Column(String(100), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    
    client_name = Column(String(200))
    total_value = Column(Float, nullable=False)
    currency = Column(String(10), default='CNY')
    
    sign_date = Column(DateTime)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    # 关联业务维度
    product_id = Column(Integer, ForeignKey('products.id'))
    organization_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    
    status = Column(String(50), default='Active')
    raw_data = Column(JSON)
    
    product = relationship("Product")
    organization = relationship("Organization")
    payment_nodes = relationship("ContractPaymentNode", back_populates="contract", cascade="all, delete-orphan")


class ContractPaymentNode(Base, TimestampMixin):
    """合同回款节点/里程碑模型。

    将合同总金额拆分为具体的收款节点，并将其技术达成条件与 GitLab/禅道中的里程碑绑定。
    通过自动化同步里程碑状态，实时计算“应收账款 (Accounts Receivable)”。

    Attributes:
        id: 自增内部主键。
        contract_id: 所属收入合同 ID。
        node_name: 节点名称 (如 预付款, UAT 验收款)。
        billing_percentage: 该节点占合同总额的百分比。
        billing_amount: 该节点的具体应收金额。
        linked_milestone_id: 关联的外部技术里程碑 ID (如 GitLab Milestone)。
        linked_system: 里程碑所在的源系统 (gitlab, zentao, jira)。
        is_achieved: 技术指标是否已达成（根据外部系统状态自动同步）。
        achieved_at: 技术指标达成的具体时间。
        is_billed: 是否已发起财务维度的开票或收款动作。
        billed_at: 实际回款或开票时间。
        contract: 关联的 RevenueContract 模型。
    """
    __tablename__ = 'contract_payment_nodes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey('revenue_contracts.id'), nullable=False)
    
    node_name = Column(String(200), nullable=False)
    billing_percentage = Column(Float) # 如 30.0 代表 30%
    billing_amount = Column(Float)     # 该节点的应收金额
    
    # 与项目的技术进度挂钩
    linked_milestone_id = Column(Integer)  # 外部系统里程碑 ID (如 GitLab Milestone)
    linked_system = Column(String(50))     # gitlab, zentao, jira
    
    # 财务进度控制
    is_achieved = Column(Boolean, default=False)
    achieved_at = Column(DateTime)
    is_billed = Column(Boolean, default=False)
    billed_at = Column(DateTime)
    
    contract = relationship("RevenueContract", back_populates="payment_nodes")


class PurchaseContract(Base, TimestampMixin):
    """采购合同模型 (Purchase Contract)。

    用于记录公司支出的各类采购合同，包括：云服务采购、人力外包、软件许可、设备租赁等。
    它是 ResourceCost 支出的源头追溯依据。

    Attributes:
        id: 自增内部主键。
        contract_no: 采购合同唯一编号。
        vendor_name: 供应商全称。
        vendor_id: 供应商在内部 SRM 或财务系统中的唯一 ID。
        title: 合同项目详细名称。
        total_amount: 合同含税总金额。
        currency: 币种 (默认 CNY)。
        start_date: 合同有效起始日期。
        end_date: 合同过期日期。
        cost_code_id: 关联的财务 CBS 科目 ID。
        capex_opex_flag: 支出性质 (CAPEX 或 OPEX)。
        status: 合同有效状态 (Active, Expired, Pending)。
        raw_data: 原始 JSON 镜像存储。
        cost_code: 关联的 CostCode 模型。
        costs: 分摊到该合同下的 ResourceCost 流水集合。
    """
    __tablename__ = 'purchase_contracts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_no = Column(String(100), unique=True, nullable=False)
    vendor_name = Column(String(200), nullable=False)
    vendor_id = Column(String(100)) # 外部供应商系统 ID
    
    title = Column(String(500), nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), default='CNY')
    
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    # 财务维度
    cost_code_id = Column(Integer, ForeignKey('cost_codes.id'))
    capex_opex_flag = Column(String(20)) # CAPEX, OPEX
    
    status = Column(String(50), default='Active')
    raw_data = Column(JSON)
    
    # 关系
    cost_code = relationship("CostCode")
    costs = relationship("ResourceCost", back_populates="purchase_contract")






class UserCredential(Base, TimestampMixin):

    """"&1WQa	vt?(mdm_credentials)?

    

    p:jMP"&1W(Rj0fVtO}m?mdm_identities RU\O[DhuO&1 D6ncmQutp ?

    

    Attributes:

        user_id: O[N(RS^p "&1W ID (UUID).

        password_hash: TrvZ^k5pUrEWJ?

        last_login_at: ȓ Z^j0fi?

    """

    __tablename__ = 'mdm_credentials'

    

    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), primary_key=True)

    password_hash = Column(String(200), nullable=False)

    last_login_at = Column(DateTime(timezone=True))

    

    user = relationship("User", backref=backref("credential", uselist=False, cascade="all, delete-orphan"))


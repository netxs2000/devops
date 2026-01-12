"""DevOps Collector 核心基础模型模块。

定义了跨插件通用的 MDM (Master Data Management) 模型、
SCD Type 2 支持、以及 RBAC 特权模型。
"""
from datetime import datetime, timezone
from typing import List, Optional, Any
import uuid
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, Text, DateTime, Date, ForeignKey, Table, JSON, Index, func, UniqueConstraint, Float, select, UUID
from sqlalchemy.orm import relationship, backref, DeclarativeBase
from sqlalchemy.ext.hybrid import hybrid_property

class Base(DeclarativeBase):
    """SQLAlchemy 声明式模型基类。"""
    pass

class TimestampMixin:
    """时间戳混入类，提供自动创建和更新时间。"""
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

class SCDMixin:
    """SCD Type 2 慢变维支持混入类。"""
    sync_version = Column(Integer, default=1, nullable=False)
    effective_from = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    effective_to = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=True, index=True)
    is_deleted = Column(Boolean, default=False)

class Organization(Base, TimestampMixin, SCDMixin):
    """组织架构表，支持 SCD Type 2 生命周期管理。"""
    __tablename__ = 'mdm_organizations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(String(100), nullable=False, unique=True, index=True)
    org_name = Column(String(200), nullable=False)
    org_level = Column(Integer, default=1)
    parent_org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), nullable=True)
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    is_active = Column(Boolean, default=True)
    cost_center = Column(String(100), nullable=True)
    parent = relationship('Organization', remote_side=[org_id], primaryjoin='Organization.parent_org_id == Organization.org_id', backref=backref('children', cascade='all'))
    manager = relationship('User', foreign_keys=[manager_user_id], back_populates='managed_organizations')
    users = relationship('User', foreign_keys='User.department_id', primaryjoin='and_(User.department_id==Organization.org_id, User.is_current==True)', back_populates='department')
    products = relationship('Product', back_populates='owner_team')

    def __repr__(self) -> str:
        """返回组织架构的字符串表示。"""
        return f"<Organization(org_id='{self.org_id}', name='{self.org_name}', version={self.sync_version})>"



class User(Base, TimestampMixin, SCDMixin):
    """全局用户映射表。"""
    __tablename__ = 'mdm_identities'
    global_user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(50), unique=True, index=True)
    username = Column(String(100))
    full_name = Column(String(200))
    primary_email = Column(String(255), unique=True, index=True)
    department_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    is_active = Column(Boolean, default=True)
    is_survivor = Column(Boolean, default=False)
    department = relationship('Organization', foreign_keys=[department_id], back_populates='users')
    managed_organizations = relationship('Organization', foreign_keys='Organization.manager_user_id', back_populates='manager')
    identities = relationship('IdentityMapping', back_populates='user')
    roles = relationship('Role', secondary='sys_user_roles', backref='users')
    test_cases = relationship('GTMTestCase', back_populates='author')
    requirements = relationship('GTMRequirement', back_populates='author')
    managed_products_as_pm = relationship('Product', back_populates='product_manager')
    project_memberships = relationship('GitLabProjectMember', back_populates='user')
    team_memberships = relationship('TeamMember', back_populates='user')
    
    total_eloc = Column(Float, default=0.0)
    eloc_rank = Column(Integer, default=0)

    @property
    def email(self) -> str:
        """返回用户主邮箱（用于模式匹配）。"""
        return self.primary_email

    @property
    def external_usernames(self) -> List[str]:
        """返回用户关联的所有外部系统用户名。"""
        return [i.external_username for i in self.identities]

    @property
    def projects(self):
        """返回用户参与的所有 GitLab 项目。"""
        return [pm.project for pm in self.project_memberships]

    def __repr__(self) -> str:
        """返回用户的字符串表示。"""
        return f"<User(name='{self.full_name}', email='{self.primary_email}', version={self.sync_version})>"

class CommitMetrics(Base, TimestampMixin):
    """单个提交的详细度量数据 (ELOC)。"""
    __tablename__ = 'commit_metrics'
    commit_id = Column(String(100), primary_key=True)
    project_id = Column(String(100), ForeignKey('mdm_projects.project_id'), nullable=True)
    author_email = Column(String(255), index=True)
    committed_at = Column(DateTime(timezone=True))
    raw_additions = Column(Integer, default=0)
    raw_deletions = Column(Integer, default=0)
    eloc_score = Column(Float, default=0.0)
    impact_score = Column(Float, default=0.0)
    churn_lines = Column(Integer, default=0)
    comment_lines = Column(Integer, default=0)
    test_lines = Column(Integer, default=0)
    file_count = Column(Integer, default=0)
    is_merge = Column(Boolean, default=False)
    is_legacy_refactor = Column(Boolean, default=False)
    refactor_ratio = Column(Float, default=0.0)

class DailyDevStats(Base, TimestampMixin):
    """开发人员行为的每日快照。"""
    __tablename__ = 'daily_dev_stats'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), index=True)
    date = Column(Date, index=True)
    first_commit_time = Column(DateTime)
    last_commit_time = Column(DateTime)
    commit_count = Column(Integer, default=0)
    total_impact = Column(Float, default=0.0)
    total_churn = Column(Integer, default=0)

class SatisfactionRecord(Base, TimestampMixin):
    """开发人员体验/满意度调查记录 (SPACE 框架中的 Satisfaction)。"""
    __tablename__ = 'satisfaction_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), index=True)
    score = Column(Integer)
    date = Column(Date, index=True)
    tags = Column(String(255), nullable=True)
    comment = Column(String(500), nullable=True)

class Role(Base):
    """系统角色参考表 (rbac_roles)。"""
    __tablename__ = 'rbac_roles'
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    permissions = relationship('Permission', secondary='sys_role_permissions', backref='roles')

class Permission(Base):
    """原子权限定义表 (rbac_permissions)。"""
    __tablename__ = 'rbac_permissions'
    code = Column(String(100), primary_key=True)
    category = Column(String(50))
    description = Column(String(255))

class RolePermission(Base):
    """角色与权限映射表。"""
    __tablename__ = 'sys_role_permissions'
    role_id = Column(Integer, ForeignKey('rbac_roles.id'), primary_key=True)
    permission_code = Column(String(100), ForeignKey('rbac_permissions.code'), primary_key=True)

class UserRole(Base):
    """用户与角色映射表。"""
    __tablename__ = 'sys_user_roles'
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('rbac_roles.id'), primary_key=True)

class IdentityMapping(Base, TimestampMixin):
    """外部身份映射表，连接 MDM 用户与第三方系统账号。"""
    __tablename__ = 'mdm_identity_mappings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    global_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), index=True)
    source_system = Column(String(50), nullable=False, index=True)
    external_user_id = Column(String(100), nullable=False)
    external_username = Column(String(100))
    external_email = Column(String(100))
    mapping_status = Column(String(20), default='VERIFIED')
    confidence_score = Column(Float, default=1.0)
    last_active_at = Column(DateTime(timezone=True))
    user = relationship('User', back_populates='identities')

class Team(Base, TimestampMixin):
    """虚拟业务团队/项目组表。"""
    __tablename__ = 'sys_teams'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    team_code = Column(String(50), unique=True, index=True)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey('sys_teams.id'), nullable=True)
    org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), nullable=True)
    leader_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    parent = relationship('Team', remote_side=[id], backref=backref('children', cascade='all, delete-orphan'))
    leader = relationship('User', foreign_keys=[leader_id])
    members = relationship('TeamMember', back_populates='team', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        """返回团队的字符串表示。"""
        return f"<Team(name='{self.name}', code='{self.team_code}')>"

class TeamMember(Base, TimestampMixin):
    """团队成员关联表。"""
    __tablename__ = 'sys_team_members'
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey('sys_teams.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=False)
    role_code = Column(String(50), default='MEMBER')
    allocation_ratio = Column(Float, default=1.0)
    team = relationship('Team', back_populates='members')
    user = relationship('User', back_populates='team_memberships')

    def __repr__(self) -> str:
        """返回成员关联的字符串表示。"""
        return f"<TeamMember(team_id={self.team_id}, user_id={self.user_id}, role={self.role_code})>"

class Product(Base, TimestampMixin):
    """产品主数据表 (mdm_product)。"""
    __tablename__ = 'mdm_product'
    product_id = Column(String(100), primary_key=True)
    product_code = Column(String(25), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    product_description = Column(Text, nullable=False)
    category = Column(String(100))
    version_schema = Column(String(50), nullable=False)
    specification = Column(JSON)
    runtime_env = Column(JSON)
    checksum = Column(String(255))
    lifecycle_status = Column(String(50), default='Active')
    repo_url = Column(String(255))
    artifact_path = Column(String(255))
    owner_team_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    product_manager_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    owner_team = relationship('Organization', back_populates='products')
    product_manager = relationship('User', back_populates='managed_products_as_pm')
    project_relations = relationship('ProjectProductRelation', back_populates='product')

    def __repr__(self) -> str:
        """返回产品的字符串表示。"""
        return f"<Product(code='{self.product_code}', name='{self.product_name}')>"

class ProjectProductRelation(Base, TimestampMixin):
    """项目与产品的关联权重表。"""
    __tablename__ = 'mdm_rel_project_product'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(100), ForeignKey('mdm_projects.project_id'), nullable=False, index=True)
    org_id = Column(String(100), nullable=False, index=True)
    product_id = Column(String(100), ForeignKey('mdm_product.product_id'), nullable=False, index=True)
    relation_type = Column(String(50), default='PRIMARY')
    allocation_ratio = Column(Float, default=1.0)
    __table_args__ = (UniqueConstraint('project_id', 'product_id', name='uq_project_product'),)
    project = relationship('ProjectMaster', back_populates='product_relations')
    product = relationship('Product', back_populates='project_relations')

class Service(Base, TimestampMixin):
    """服务目录表。"""
    __tablename__ = 'mdm_services'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    tier = Column(String(20))
    org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), nullable=True)
    description = Column(Text)
    organization = relationship('Organization')
    costs = relationship('ResourceCost', back_populates='service')
    slos = relationship('SLO', back_populates='service', cascade='all, delete-orphan')
    project_mappings = relationship('ServiceProjectMapping', back_populates='service', cascade='all, delete-orphan')

    @property
    def total_cost(self) -> float:
        """计算服务的总资源成本。"""
        return sum((c.amount for c in self.costs))

    @property
    def investment_roi(self) -> float:
        """计算服务的投资回报率 (ROI)。"""
        return 10.0 if self.total_cost > 0 else 0.0

class ResourceCost(Base, TimestampMixin):
    """资源成本记录明细表。"""
    __tablename__ = 'stg_mdm_resource_costs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey('mdm_services.id'), nullable=True)
    cost_code_id = Column(Integer, ForeignKey('mdm_cost_codes.id'), nullable=True)
    purchase_contract_id = Column(Integer, ForeignKey('mdm_purchase_contracts.id'), nullable=True)
    period = Column(String(20), index=True) # YYYY-MM
    amount = Column(Float, default=0.0)
    currency = Column(String(10), default='CNY')
    cost_type = Column(String(50))
    cost_item = Column(String(200))
    vendor_name = Column(String(200))
    capex_opex_flag = Column(String(10))
    source_system = Column(String(100))
    service = relationship('Service', back_populates='costs')
    cost_code = relationship('CostCode')
    purchase_contract = relationship('PurchaseContract')

class MetricDefinition(Base, TimestampMixin):
    """指标定义表，定义系统中支持的所有效能指标。"""
    __tablename__ = 'mdm_metric_definitions'
    metric_code = Column(String(100), primary_key=True)
    metric_name = Column(String(200), nullable=False)
    domain = Column(String(50), nullable=False)

class SystemRegistry(Base, TimestampMixin):
    """三方系统注册表，记录对接的所有外部系统 (GitLab, Jira, Sonar 等)。"""
    __tablename__ = 'mdm_systems_registry'
    system_code = Column(String(50), primary_key=True)
    system_name = Column(String(100), nullable=False)

class EntityTopology(Base):
    """实体拓扑关系表，记录不同系统实体间的映射关系。"""
    __tablename__ = 'mdm_entities_topology'
    id = Column(Integer, primary_key=True)
    entity_id = Column(String(100), index=True)
    target_id = Column(String(100))
    internal_id = Column(String(100))
    is_current = Column(Boolean, default=True)
    sync_version = Column(Integer, default=1)

class SyncLog(Base, TimestampMixin):
    """插件数据同步日志记录表。"""
    __tablename__ = 'sys_sync_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(100), index=True)
    status = Column(String(50))
    message = Column(Text)

class Location(Base, TimestampMixin):
    """地理位置或机房位置参考表。"""
    __tablename__ = 'mdm_locations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(String(50), unique=True, index=True)
    location_name = Column(String(200), nullable=False)
    short_name = Column(String(50))
    location_type = Column(String(50)) # country, province, city, datacenter
    parent_id = Column(String(50))
    region = Column(String(50)) # 华北, 华东, etc.
    is_active = Column(Boolean, default=True)
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)

class Calendar(Base, TimestampMixin):
    """公共日历/节假日参考表。"""
    __tablename__ = 'mdm_calendar'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_day = Column(Date, unique=True, index=True, nullable=False)
    year_number = Column(Integer, index=True)
    month_number = Column(Integer)
    quarter_number = Column(Integer)
    day_of_week = Column(Integer)
    is_workday = Column(Boolean, default=True)
    is_holiday = Column(Boolean, default=False)
    holiday_name = Column(String(100))
    fiscal_year = Column(String(20))
    fiscal_quarter = Column(String(20))
    week_of_year = Column(Integer)
    season_tag = Column(String(20))

class RawDataStaging(Base):
    """原始数据暂存表 (Staging 层)，用于存放未经处理的 API Payload。"""
    __tablename__ = 'stg_raw_data'
    id = Column(Integer, primary_key=True)
    source = Column(String(50))
    entity_type = Column(String(50))
    external_id = Column(String(100))
    payload = Column(JSON)
    schema_version = Column(String(20))
    collected_at = Column(DateTime(timezone=True))

class OKRObjective(Base, TimestampMixin):
    """OKR 目标定义表。"""
    __tablename__ = 'mdm_okr_objectives'
    id = Column(Integer, primary_key=True, autoincrement=True)
    objective_id = Column(String(50), unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    period = Column(String(20), index=True) # e.g., '2024-Q1'
    owner_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    status = Column(String(20), default='ACTIVE') # ACTIVE, COMPLETED, ABANDONED
    progress = Column(Float, default=0.0)
    
    owner = relationship('User')
    organization = relationship('Organization')
    key_results = relationship('OKRKeyResult', back_populates='objective', cascade='all, delete-orphan')

class OKRKeyResult(Base, TimestampMixin):
    """OKR 关键结果 (KR) 定义表。"""
    __tablename__ = 'mdm_okr_key_results'
    id = Column(Integer, primary_key=True, autoincrement=True)
    objective_id = Column(Integer, ForeignKey('mdm_okr_objectives.id'), nullable=False)
    title = Column(String(255), nullable=False)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0.0)
    unit = Column(String(20)) # %, days, etc.
    weight = Column(Float, default=1.0)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    progress = Column(Float, default=0.0)
    
    objective = relationship('OKRObjective', back_populates='key_results')
    owner = relationship('User')

class TraceabilityLink(Base):
    """跨系统追溯链路表，连接需求与代码、测试与发布。"""
    __tablename__ = 'mdm_traceability_links'
    id = Column(Integer, primary_key=True)
    source_system = Column(String(50))
    source_type = Column(String(50))
    source_id = Column(String(100))
    target_system = Column(String(50))
    target_type = Column(String(50))
    target_id = Column(String(100))
    link_type = Column(String(50))
    raw_data = Column(JSON)

class TestExecutionSummary(Base):
    """测试执行汇总记录表。"""
    __tablename__ = 'fct_test_execution_summary'
    id = Column(Integer, primary_key=True)

class PerformanceRecord(Base):
    """效能/性能表现评估记录表。"""
    __tablename__ = 'fct_performance_records'
    id = Column(Integer, primary_key=True)

class Incident(Base):
    """线上事故/线上问题记录表。"""
    __tablename__ = 'mdm_incidents'
    id = Column(Integer, primary_key=True)

class UserActivityProfile(Base):
    """用户活跃度画像快照表。"""
    __tablename__ = 'fct_user_activity_profiles'
    id = Column(BigInteger, primary_key=True)

class ServiceProjectMapping(Base, TimestampMixin):
    """服务与工程项目的多对多关联映射表。"""
    __tablename__ = 'mdm_service_project_mapping'
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey('mdm_services.id'), nullable=False)
    source = Column(String(50)) # gitlab, jira, etc.
    project_id = Column(Integer) # or UUID depending on system
    service = relationship('Service', back_populates='project_mappings')

class SLO(Base, TimestampMixin):
    """SLO (服务水平目标) 定义表。"""
    __tablename__ = 'mdm_slo_definitions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey('mdm_services.id'), nullable=False)
    name = Column(String(100), nullable=False)
    indicator_type = Column(String(50)) # Availability, Latency, etc.
    target_value = Column(Float)
    metric_unit = Column(String(20)) # %, ms, etc.
    time_window = Column(String(20)) # 28d, 7d
    service = relationship('Service', back_populates='slos')

class ProjectMaster(Base, TimestampMixin, SCDMixin):
    """项目全生命周期主数据 (mdm_projects)。"""
    __tablename__ = 'mdm_projects'
    project_id = Column(String(100), primary_key=True)
    project_name = Column(String(200), nullable=False)
    project_type = Column(String(50))
    status = Column(String(50), default='PLAN')
    is_active = Column(Boolean, default=True)
    pm_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    plan_start_date = Column(Date)
    plan_end_date = Column(Date)
    actual_start_at = Column(DateTime(timezone=True))
    actual_end_at = Column(DateTime(timezone=True))
    external_id = Column(String(100), unique=True)
    system_code = Column(String(50), ForeignKey('mdm_systems_registry.system_code'))
    budget_code = Column(String(100))
    budget_type = Column(String(50))
    lead_repo_id = Column(Integer, nullable=True)
    description = Column(Text)
    organization = relationship('Organization', foreign_keys=[org_id])
    project_manager = relationship('User', foreign_keys=[pm_user_id])
    source_system = relationship('SystemRegistry')
    gitlab_repos = relationship('GitLabProject', back_populates='mdm_project')
    product_relations = relationship('ProjectProductRelation', back_populates='project')

    def __repr__(self) -> str:
        """返回项目主数据的字符串表示。"""
        return f"<ProjectMaster(project_id='{self.project_id}', name='{self.project_name}')>"

class CostCode(Base, TimestampMixin):
    """成本科目 (CBS) 模型。"""
    __tablename__ = 'mdm_cost_codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50))
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey('mdm_cost_codes.id'), nullable=True)
    default_capex_opex = Column(String(10))
    is_active = Column(Boolean, default=True)
    parent = relationship('CostCode', remote_side=[id], backref='children')

class LaborRateConfig(Base, TimestampMixin):
    """人工标准费率配置表。"""
    __tablename__ = 'mdm_labor_rate_config'
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_title_level = Column(String(50), nullable=False)
    daily_rate = Column(Float, nullable=False)
    hourly_rate = Column(Float)
    currency = Column(String(10), default='CNY')
    effective_date = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)

class RevenueContract(Base, TimestampMixin):
    """销售/收入合同主数据表格。"""
    __tablename__ = 'mdm_revenue_contracts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_no = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255))
    client_name = Column(String(255))
    total_value = Column(Float, default=0.0)
    currency = Column(String(10), default='CNY')
    sign_date = Column(Date)
    product_id = Column(String(100), ForeignKey('mdm_product.product_id'), nullable=True)
    product = relationship('Product')
    payment_nodes = relationship('ContractPaymentNode', back_populates='contract', cascade='all, delete-orphan')

class PurchaseContract(Base, TimestampMixin):
    """采购/支出合同主数据。"""
    __tablename__ = 'mdm_purchase_contracts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_no = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255))
    vendor_name = Column(String(255))
    vendor_id = Column(String(100))
    total_amount = Column(Float, default=0.0)
    currency = Column(String(10), default='CNY')
    start_date = Column(Date)
    end_date = Column(Date)
    cost_code_id = Column(Integer, ForeignKey('mdm_cost_codes.id'), nullable=True)
    capex_opex_flag = Column(String(10))
    cost_code = relationship('CostCode')

class ContractPaymentNode(Base, TimestampMixin):
    """合同付款节点/收款计划记录表。"""
    __tablename__ = 'mdm_contract_payment_nodes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey('mdm_revenue_contracts.id'), nullable=False)
    node_name = Column(String(200), nullable=False)
    billing_percentage = Column(Float)
    billing_amount = Column(Float)
    linked_system = Column(String(50)) # gitlab, jira, manual
    linked_milestone_id = Column(Integer)
    is_achieved = Column(Boolean, default=False)
    achieved_at = Column(DateTime(timezone=True))
    contract = relationship('RevenueContract', back_populates='payment_nodes')

class UserCredential(Base, TimestampMixin):
    """用户凭证表。"""
    __tablename__ = 'sys_user_credentials'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), unique=True)
    password_hash = Column(String(255), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    user = relationship('User', backref=backref('credential', uselist=False))

class UserOAuthToken(Base, TimestampMixin):
    """用户 OAuth 令牌存储表。"""
    __tablename__ = 'sys_user_oauth_tokens'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), index=True)
    provider = Column(String(50), index=True)
    access_token = Column(String(1024), nullable=False)
    refresh_token = Column(String(1024))
    token_type = Column(String(50))
    expires_at = Column(DateTime(timezone=True))

class Company(Base):
    """公司实体参考表。"""
    __tablename__ = 'mdm_company'
    company_id = Column(String(50), primary_key=True)

class Vendor(Base):
    """外部供应商参考表。"""
    __tablename__ = 'mdm_vendor'
    vendor_code = Column(String(50), primary_key=True)

class EpicMaster(Base):
    """跨团队/长期史诗需求 (Epic) 主数据。"""
    __tablename__ = 'mdm_epic'
    id = Column(Integer, primary_key=True)

class ComplianceIssue(Base):
    """合规风险与审计问题记录表。"""
    __tablename__ = 'mdm_compliance_issues'
    id = Column(Integer, primary_key=True)
    issue_type = Column(String(50))
    severity = Column(String(20))
    entity_id = Column(String(100))
    status = Column(String(20))
    description = Column(Text)
    metadata_payload = Column(JSON)

class RawDataMixin:
    """原始数据支持混入类。"""
    pass
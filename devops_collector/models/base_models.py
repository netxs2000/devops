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
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    org_id = Column(String(100), nullable=False, unique=True, index=True, comment='组织唯一标识 (HR系统同步)')
    org_name = Column(String(200), nullable=False, comment='组织名称')
    org_level = Column(Integer, default=1, comment='组织层级 (1=公司, 2=部门, 3=团队)')
    parent_org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), nullable=True, comment='上级组织ID')
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), comment='部门负责人用户ID')
    is_active = Column(Boolean, default=True, comment='是否启用')
    cost_center = Column(String(100), nullable=True, comment='成本中心编码')
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
    global_user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment='全局唯一用户标识')
    employee_id = Column(String(50), unique=True, index=True, comment='HR系统工号')
    username = Column(String(100), comment='登录用户名')
    full_name = Column(String(200), comment='用户姓名')
    primary_email = Column(String(255), unique=True, index=True, comment='主邮箱地址')
    department_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), comment='所属部门ID')
    is_active = Column(Boolean, default=True, comment='是否在职')
    is_survivor = Column(Boolean, default=False, comment='是否通过合并保留的账号')
    department = relationship('Organization', foreign_keys=[department_id], back_populates='users')
    managed_organizations = relationship('Organization', foreign_keys='Organization.manager_user_id', back_populates='manager')
    identities = relationship('IdentityMapping', back_populates='user')
    roles = relationship('Role', secondary='sys_user_roles', backref='users')
    test_cases = relationship('GTMTestCase', back_populates='author')
    requirements = relationship('GTMRequirement', back_populates='author')
    managed_products_as_pm = relationship('Product', back_populates='product_manager')
    project_memberships = relationship('GitLabProjectMember', back_populates='user')
    team_memberships = relationship('TeamMember', back_populates='user')
    
    total_eloc = Column(Float, default=0.0, comment='累计有效代码行数')
    eloc_rank = Column(Integer, default=0, comment='ELOC排名')

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

    @property
    def role(self) -> str:
        """返回用户的第一个主要角色代码，默认为 'user'。"""
        if self.roles:
            return self.roles[0].code
        return 'user'

    def __repr__(self) -> str:
        """返回用户的字符串表示。"""
        return f"<User(name='{self.full_name}', email='{self.primary_email}', version={self.sync_version})>"

class CommitMetrics(Base, TimestampMixin):
    """单个提交的详细度量数据 (ELOC)。"""
    __tablename__ = 'commit_metrics'
    commit_id = Column(String(100), primary_key=True, comment='提交SHA哈希值')
    project_id = Column(String(100), ForeignKey('mdm_projects.project_id'), nullable=True, comment='所属业务项目ID')
    author_email = Column(String(255), index=True, comment='提交者邮箱')
    committed_at = Column(DateTime(timezone=True), comment='提交时间')
    raw_additions = Column(Integer, default=0, comment='原始新增行数')
    raw_deletions = Column(Integer, default=0, comment='原始删除行数')
    eloc_score = Column(Float, default=0.0, comment='有效代码行数得分')
    impact_score = Column(Float, default=0.0, comment='代码影响力得分')
    churn_lines = Column(Integer, default=0, comment='代码翻动行数')
    comment_lines = Column(Integer, default=0, comment='注释行数')
    test_lines = Column(Integer, default=0, comment='测试代码行数')
    file_count = Column(Integer, default=0, comment='涉及文件数')
    is_merge = Column(Boolean, default=False, comment='是否为合并提交')
    is_legacy_refactor = Column(Boolean, default=False, comment='是否为遗留代码重构')
    refactor_ratio = Column(Float, default=0.0, comment='重构代码占比')

class DailyDevStats(Base, TimestampMixin):
    """开发人员行为的每日快照。"""
    __tablename__ = 'daily_dev_stats'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), index=True, comment='用户ID')
    date = Column(Date, index=True, comment='统计日期')
    first_commit_time = Column(DateTime, comment='当日首次提交时间')
    last_commit_time = Column(DateTime, comment='当日最后提交时间')
    commit_count = Column(Integer, default=0, comment='当日提交次数')
    total_impact = Column(Float, default=0.0, comment='当日总影响力得分')
    total_churn = Column(Integer, default=0, comment='当日总代码翻动行数')

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
    id = Column(Integer, primary_key=True, comment='角色ID')
    code = Column(String(50), unique=True, nullable=False, comment='角色代码 (admin/pm/dev/viewer)')
    name = Column(String(100), unique=True, nullable=False, comment='角色显示名称')
    description = Column(String(255), comment='角色描述')
    permissions = relationship('Permission', secondary='sys_role_permissions', backref='roles')

class Permission(Base):
    """原子权限定义表 (rbac_permissions)。"""
    __tablename__ = 'rbac_permissions'
    code = Column(String(100), primary_key=True, comment='权限代码 (如 ticket:create)')
    category = Column(String(50), comment='权限分类 (ticket/project/admin)')
    description = Column(String(255), comment='权限描述')

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
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    global_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), index=True, comment='全局用户ID')
    source_system = Column(String(50), nullable=False, index=True, comment='来源系统 (gitlab/jira/sonar)')
    external_user_id = Column(String(100), nullable=False, comment='外部系统用户ID')
    external_username = Column(String(100), comment='外部系统用户名')
    external_email = Column(String(100), comment='外部系统邮箱')
    mapping_status = Column(String(20), default='VERIFIED', comment='映射状态 (VERIFIED/PENDING/REJECTED)')
    confidence_score = Column(Float, default=1.0, comment='匹配置信度 (0.0-1.0)')
    last_active_at = Column(DateTime(timezone=True), comment='最后活跃时间')
    user = relationship('User', back_populates='identities')

class Team(Base, TimestampMixin):
    """虚拟业务团队/项目组表。"""
    __tablename__ = 'sys_teams'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    name = Column(String(100), nullable=False, comment='团队名称')
    team_code = Column(String(50), unique=True, index=True, comment='团队代码')
    description = Column(Text, comment='团队描述')
    parent_id = Column(Integer, ForeignKey('sys_teams.id'), nullable=True, comment='上级团队ID')
    org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), nullable=True, comment='所属组织ID')
    leader_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True, comment='团队负责人ID')
    parent = relationship('Team', remote_side=[id], backref=backref('children', cascade='all, delete-orphan'))
    leader = relationship('User', foreign_keys=[leader_id])
    members = relationship('TeamMember', back_populates='team', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        """返回团队的字符串表示。"""
        return f"<Team(name='{self.name}', code='{self.team_code}')>"

class TeamMember(Base, TimestampMixin):
    """团队成员关联表。"""
    __tablename__ = 'sys_team_members'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    team_id = Column(Integer, ForeignKey('sys_teams.id'), nullable=False, comment='团队ID')
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=False, comment='成员用户ID')
    role_code = Column(String(50), default='MEMBER', comment='团队角色 (LEADER/MEMBER/CONSULTANT)')
    allocation_ratio = Column(Float, default=1.0, comment='工作量分配比例 (0.0-1.0)')
    team = relationship('Team', back_populates='members')
    user = relationship('User', back_populates='team_memberships')

    def __repr__(self) -> str:
        """返回成员关联的字符串表示。"""
        return f"<TeamMember(team_id={self.team_id}, user_id={self.user_id}, role={self.role_code})>"

class Product(Base, TimestampMixin):
    """产品主数据表 (mdm_product)。"""
    __tablename__ = 'mdm_product'
    product_id = Column(String(100), primary_key=True, comment='产品唯一标识')
    product_code = Column(String(25), nullable=False, index=True, comment='产品编码')
    product_name = Column(String(255), nullable=False, comment='产品名称')
    product_description = Column(Text, nullable=False, comment='产品描述')
    category = Column(String(100), comment='产品分类 (平台/应用/组件)')
    version_schema = Column(String(50), nullable=False, comment='版本命名规则 (SemVer/CalVer)')
    specification = Column(JSON, comment='产品规格配置 (JSON)')
    runtime_env = Column(JSON, comment='运行环境配置 (JSON)')
    checksum = Column(String(255), comment='最新版本校验码')
    lifecycle_status = Column(String(50), default='Active', comment='生命周期状态 (Active/Deprecated/EOL)')
    repo_url = Column(String(255), comment='主代码仓库URL')
    artifact_path = Column(String(255), comment='制品存储路径')
    owner_team_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), comment='负责团队ID')
    product_manager_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), comment='产品经理ID')
    owner_team = relationship('Organization', back_populates='products')
    product_manager = relationship('User', back_populates='managed_products_as_pm')
    project_relations = relationship('ProjectProductRelation', back_populates='product')

    def __repr__(self) -> str:
        """返回产品的字符串表示。"""
        return f"<Product(code='{self.product_code}', name='{self.product_name}')>"

class ProjectProductRelation(Base, TimestampMixin):
    """项目与产品的关联权重表。"""
    __tablename__ = 'mdm_rel_project_product'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    project_id = Column(String(100), ForeignKey('mdm_projects.project_id'), nullable=False, index=True, comment='项目ID')
    org_id = Column(String(100), nullable=False, index=True, comment='所属组织ID')
    product_id = Column(String(100), ForeignKey('mdm_product.product_id'), nullable=False, index=True, comment='产品ID')
    relation_type = Column(String(50), default='PRIMARY', comment='关联类型 (PRIMARY/SECONDARY)')
    allocation_ratio = Column(Float, default=1.0, comment='工作量分配比例')
    __table_args__ = (UniqueConstraint('project_id', 'product_id', name='uq_project_product'),)
    project = relationship('ProjectMaster', back_populates='product_relations')
    product = relationship('Product', back_populates='project_relations')

class BusinessSystem(Base, TimestampMixin):
    """业务系统模型 (Backstage System Concept).
    
    代表一组协作提供业务能力的组件集合 (e.g. 交易系统, 用户中心)。
    """
    __tablename__ = 'mdm_business_systems'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True) # metadata.name
    name = Column(String(100), nullable=False)
    description = Column(Text)
    domain = Column(String(50)) # e.g. 电商域, 供应链域
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    
    # Relationships
    services = relationship('Service', back_populates='system')
    owner = relationship('User')

class Service(Base, TimestampMixin):
    """服务/组件目录表 (Extended with Backstage Component Model)."""
    __tablename__ = 'mdm_services'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    name = Column(String(200), nullable=False, comment='服务名称')
    tier = Column(String(20), comment='服务级别 (T0/T1/T2/T3)')
    org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), nullable=True, comment='负责组织ID')
    description = Column(Text, comment='服务描述')
    
    # --- Backstage 扩展字段 ---
    system_id = Column(Integer, ForeignKey('mdm_business_systems.id'), nullable=True, comment='所属业务系统ID')
    
    # spec.lifecycle (experimental, production, deprecated)
    lifecycle = Column(String(20), default='production', comment='生命周期 (experimental/production/deprecated)')
    
    # spec.type (service, library, website, tool)
    component_type = Column(String(20), default='service', comment='组件类型 (service/library/website/tool)')
    
    # metadata.tags & links
    tags = Column(JSON, comment='标签列表 (JSON)')
    links = Column(JSON, comment='相关链接 (JSON)')
    
    # --- 现有关系 ---
    system = relationship('BusinessSystem', back_populates='services')
    organization = relationship('Organization')
    costs = relationship('ResourceCost', back_populates='service')
    slos = relationship('SLO', back_populates='service', cascade='all, delete-orphan')
    project_mappings = relationship('ServiceProjectMapping', back_populates='service', cascade='all, delete-orphan')
    
    # 新增资源映射关系
    resources = relationship('EntityTopology', back_populates='service', cascade='all, delete-orphan')

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
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    service_id = Column(Integer, ForeignKey('mdm_services.id'), nullable=True, comment='关联服务ID')
    cost_code_id = Column(Integer, ForeignKey('mdm_cost_codes.id'), nullable=True, comment='成本科目ID')
    purchase_contract_id = Column(Integer, ForeignKey('mdm_purchase_contracts.id'), nullable=True, comment='采购合同ID')
    period = Column(String(20), index=True, comment='费用周期 (YYYY-MM)')
    amount = Column(Float, default=0.0, comment='费用金额')
    currency = Column(String(10), default='CNY', comment='币种')
    cost_type = Column(String(50), comment='成本类型 (云资源/人力/软件)')
    cost_item = Column(String(200), comment='成本项目名称')
    vendor_name = Column(String(200), comment='供应商名称')
    capex_opex_flag = Column(String(10), comment='CAPEX/OPEX标志')
    source_system = Column(String(100), comment='数据来源系统')
    service = relationship('Service', back_populates='costs')
    cost_code = relationship('CostCode')
    purchase_contract = relationship('PurchaseContract')

class MetricDefinition(Base, TimestampMixin):
    """指标语义定义表 (mdm_metric_definitions)。
    这是 "指标字典" 的核心，确保全集团计算逻辑一致 (Single Source of Truth)。
    """
    __tablename__ = 'mdm_metric_definitions'

    # 1. 基础信息
    metric_code = Column(String(100), primary_key=True)  # e.g., DORA_MTTR_PROD
    metric_name = Column(String(200), nullable=False)    # e.g., 生产环境平均修复时间
    domain = Column(String(50), nullable=False)          # DEVOPS, FINANCE, OPERATION
    metric_type = Column(String(50))                     # ATOMIC(原子), DERIVED(派生), COMPOSITE(复合)
    
    # 2. 计算逻辑
    calculation_logic = Column(Text)       # 计算公式或 dbt 模型路径
    unit = Column(String(50))              # %, ms, Hours, Count
    aggregate_type = Column(String(20))    # SUM, AVG, COUNT, MAX, MIN
    source_model = Column(String(200))     # 来源模型名称 (关联 dbt 模型或表)
    
    # 3. 维度与约束
    dimension_scope = Column(JSON)         # 允许挂载的维度列表 (JSON List) ["dept", "app", "priority"]
    is_standard = Column(Boolean, default=True) # 是否集团标准指标 (涉及口径锁定)
    
    # 4. 治理与归属
    business_owner_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    
    # 5. 时效性
    time_grain = Column(String(50))   # Daily, Weekly, Monthly
    update_cycle = Column(String(50)) # Realtime, T+1, Hourly
    
    # 6. 生命周期
    status = Column(String(50), default='RELEASED') # DRAFT, RELEASED, DEPRECATED
    is_active = Column(Boolean, default=True)       # 逻辑删除标志

    # Relationships
    business_owner = relationship('User', foreign_keys=[business_owner_id])
    
    def __repr__(self):
        return f"<MetricDefinition(code='{self.metric_code}', name='{self.metric_name}')>"

class SystemRegistry(Base, TimestampMixin):
    """三方系统注册表，记录对接的所有外部系统 (GitLab, Jira, Sonar 等)。
    
    作为数据源治理注册中心，定义了连接方式、同步策略及数据治理属性。
    """
    __tablename__ = 'mdm_systems_registry'
    system_code = Column(String(50), primary_key=True)
    system_name = Column(String(100), nullable=False)
    system_type = Column(String(50))  # VCS, TICKET, CI, SONAR
    
    # 接口与连接配置
    base_url = Column(String(255))
    api_version = Column(String(20))  # e.g., v4
    auth_type = Column(String(50))    # OAuth2, Token, User_Pass
    
    # 数据同步策略
    sync_method = Column(String(50))  # CDC, API Polling, Webhook
    update_cycle = Column(String(50)) # Realtime, Hourly, Daily
    
    # 数据治理与安全
    data_sensitivity = Column(String(20)) # L3 (机密), L2, L1
    sla_level = Column(String(20))        # P1 (核心系统)
    technical_owner_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    
    # 状态监控
    is_active = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime(timezone=True))
    remarks = Column(Text)

    technical_owner = relationship('User', foreign_keys=[technical_owner_id])
    projects = relationship('ProjectMaster', back_populates='source_system')

class EntityTopology(Base, TimestampMixin):
    """实体-资源映射表 (Infrastructure Mapping).
    
    将逻辑上的业务服务 (Service) 绑定到物理上的基础设施资源 (GitLab Repo, Sonar Project, Jenkins Job)。
    它是连接 "业务架构" (Service) 与 "工具设施" (SystemRegistry) 的胶水层。
    """
    __tablename__ = 'mdm_entity_topology'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 1. 逻辑侧 (Who) - 指向业务服务
    service_id = Column(Integer, ForeignKey('mdm_services.id'), nullable=False, index=True)
    
    # 2. 物理侧 (Where) - 指向外部工具资源
    # 明确指出是哪个系统实例 (e.g. gitlab-corp) 下的哪个资源 ID (e.g. project-1024)
    system_code = Column(String(50), ForeignKey('mdm_systems_registry.system_code'), nullable=False)
    external_resource_id = Column(String(100), nullable=False) # 原 target_id
    
    # 3. 关系定义 (What)
    # 资源类型: source-code, ci-pipeline, quality-gate, deployment-target, database
    element_type = Column(String(50), default='source-code')
    
    # 4. 状态与元数据
    is_active = Column(Boolean, default=True)
    last_verified_at = Column(DateTime(timezone=True)) # 采集器上次确认连接有效的时间
    meta_info = Column(JSON) # 存储额外的连接信息 (如 webhook_id, bind_key)

    # Relationships
    service = relationship('Service', back_populates='resources')
    target_system = relationship('SystemRegistry')
    is_current = Column(Boolean, default=True)
    sync_version = Column(Integer, default=1)

class SyncLog(Base, TimestampMixin):
    """插件数据同步日志记录表。"""
    __tablename__ = 'sys_sync_logs'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    project_id = Column(String(100), index=True, comment='关联项目ID')
    status = Column(String(50), comment='同步状态 (SUCCESS/FAILED/RUNNING)')
    message = Column(Text, comment='同步结果信息')

class Location(Base, TimestampMixin):
    """地理位置或机房位置参考表。"""
    __tablename__ = 'mdm_locations'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    location_id = Column(String(50), unique=True, index=True, comment='位置唯一标识')
    location_name = Column(String(200), nullable=False, comment='位置名称')
    short_name = Column(String(50), comment='简称')
    location_type = Column(String(50), comment='位置类型 (country/province/city/datacenter)')
    parent_id = Column(String(50), comment='上级位置ID')
    region = Column(String(50), comment='区域 (华北/华东/华南)')
    is_active = Column(Boolean, default=True, comment='是否启用')
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True, comment='负责人ID')

class Calendar(Base, TimestampMixin):
    """公共日历/节假日参考表。"""
    __tablename__ = 'mdm_calendar'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    date_day = Column(Date, unique=True, index=True, nullable=False, comment='日期')
    year_number = Column(Integer, index=True, comment='年份')
    month_number = Column(Integer, comment='月份 (1-12)')
    quarter_number = Column(Integer, comment='季度 (1-4)')
    day_of_week = Column(Integer, comment='星期几 (1=周一, 7=周日)')
    is_workday = Column(Boolean, default=True, comment='是否工作日')
    is_holiday = Column(Boolean, default=False, comment='是否节假日')
    holiday_name = Column(String(100), comment='节假日名称')
    fiscal_year = Column(String(20), comment='财年')
    fiscal_quarter = Column(String(20), comment='财务季度')
    week_of_year = Column(Integer, comment='年内周数')
    season_tag = Column(String(20), comment='季节标签 (春/夏/秋/冬)')

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
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    objective_id = Column(String(50), unique=True, index=True, comment='目标唯一标识')
    title = Column(String(255), nullable=False, comment='目标标题')
    description = Column(Text, comment='目标描述')
    period = Column(String(20), index=True, comment='周期 (2024-Q1/2024-H1)')
    owner_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), comment='负责人ID')
    org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), comment='所属组织ID')
    status = Column(String(20), default='ACTIVE', comment='状态 (ACTIVE/COMPLETED/ABANDONED)')
    progress = Column(Float, default=0.0, comment='进度 (0.0-1.0)')
    
    owner = relationship('User')
    organization = relationship('Organization')
    key_results = relationship('OKRKeyResult', back_populates='objective', cascade='all, delete-orphan')

class OKRKeyResult(Base, TimestampMixin):
    """OKR 关键结果 (KR) 定义表。"""
    __tablename__ = 'mdm_okr_key_results'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    objective_id = Column(Integer, ForeignKey('mdm_okr_objectives.id'), nullable=False, comment='关联目标ID')
    title = Column(String(255), nullable=False, comment='KR标题')
    target_value = Column(Float, nullable=False, comment='目标值')
    current_value = Column(Float, default=0.0, comment='当前值')
    unit = Column(String(20), comment='单位 (%/天/个)')
    weight = Column(Float, default=1.0, comment='权重')
    owner_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), comment='负责人ID')
    progress = Column(Float, default=0.0, comment='进度 (0.0-1.0)')
    
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
    project_id = Column(String(100), primary_key=True, comment='项目唯一标识')
    project_name = Column(String(200), nullable=False, comment='项目名称')
    project_type = Column(String(50), comment='项目类型 (研发项目/运维项目/POC)')
    status = Column(String(50), default='PLAN', comment='项目状态 (PLAN/ACTIVE/SUSPENDED/CLOSED)')
    is_active = Column(Boolean, default=True, comment='是否启用')
    pm_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True, comment='项目经理ID')
    org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), comment='负责部门ID')
    plan_start_date = Column(Date, comment='计划开始日期')
    plan_end_date = Column(Date, comment='计划结束日期')
    actual_start_at = Column(DateTime(timezone=True), comment='实际开始时间')
    actual_end_at = Column(DateTime(timezone=True), comment='实际结束时间')
    external_id = Column(String(100), unique=True, comment='外部系统项目ID')
    system_code = Column(String(50), ForeignKey('mdm_systems_registry.system_code'), comment='数据来源系统')
    budget_code = Column(String(100), comment='预算编码')
    budget_type = Column(String(50), comment='预算类型 (CAPEX/OPEX)')
    lead_repo_id = Column(Integer, nullable=True, comment='主代码仓库ID')
    description = Column(Text, comment='项目描述')
    organization = relationship('Organization', foreign_keys=[org_id])
    project_manager = relationship('User', foreign_keys=[pm_user_id])
    source_system = relationship('SystemRegistry', back_populates='projects')
    gitlab_repos = relationship('GitLabProject', back_populates='mdm_project')
    product_relations = relationship('ProjectProductRelation', back_populates='project')

    def __repr__(self) -> str:
        """返回项目主数据的字符串表示。"""
        return f"<ProjectMaster(project_id='{self.project_id}', name='{self.project_name}')>"

class CostCode(Base, TimestampMixin):
    """成本科目 (CBS) 模型。"""
    __tablename__ = 'mdm_cost_codes'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    code = Column(String(50), unique=True, nullable=False, index=True, comment='科目编码')
    name = Column(String(200), nullable=False, comment='科目名称')
    category = Column(String(50), comment='科目分类 (人力/硬件/软件/服务)')
    description = Column(Text, comment='科目描述')
    parent_id = Column(Integer, ForeignKey('mdm_cost_codes.id'), nullable=True, comment='上级科目ID')
    default_capex_opex = Column(String(10), comment='默认CAPEX/OPEX属性')
    is_active = Column(Boolean, default=True, comment='是否启用')
    parent = relationship('CostCode', remote_side=[id], backref='children')

class LaborRateConfig(Base, TimestampMixin):
    """人工标准费率配置表。"""
    __tablename__ = 'mdm_labor_rate_config'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    job_title_level = Column(String(50), nullable=False, comment='职级 (P5/P6/P7/M1/M2)')
    daily_rate = Column(Float, nullable=False, comment='日费率 (元)')
    hourly_rate = Column(Float, comment='时费率 (元)')
    currency = Column(String(10), default='CNY', comment='币种')
    effective_date = Column(DateTime(timezone=True), comment='生效日期')
    is_active = Column(Boolean, default=True, comment='是否启用')

class RevenueContract(Base, TimestampMixin):
    """销售/收入合同主数据表格。"""
    __tablename__ = 'mdm_revenue_contracts'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    contract_no = Column(String(100), unique=True, nullable=False, index=True, comment='合同编号')
    title = Column(String(255), comment='合同标题')
    client_name = Column(String(255), comment='客户名称')
    total_value = Column(Float, default=0.0, comment='合同总额')
    currency = Column(String(10), default='CNY', comment='币种')
    sign_date = Column(Date, comment='签约日期')
    product_id = Column(String(100), ForeignKey('mdm_product.product_id'), nullable=True, comment='关联产品ID')
    product = relationship('Product')
    payment_nodes = relationship('ContractPaymentNode', back_populates='contract', cascade='all, delete-orphan')

class PurchaseContract(Base, TimestampMixin):
    """采购/支出合同主数据。"""
    __tablename__ = 'mdm_purchase_contracts'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    contract_no = Column(String(100), unique=True, nullable=False, index=True, comment='合同编号')
    title = Column(String(255), comment='合同标题')
    vendor_name = Column(String(255), comment='供应商名称')
    vendor_id = Column(String(100), comment='供应商ID')
    total_amount = Column(Float, default=0.0, comment='合同总额')
    currency = Column(String(10), default='CNY', comment='币种')
    start_date = Column(Date, comment='合同开始日期')
    end_date = Column(Date, comment='合同结束日期')
    cost_code_id = Column(Integer, ForeignKey('mdm_cost_codes.id'), nullable=True, comment='成本科目ID')
    capex_opex_flag = Column(String(10), comment='CAPEX/OPEX标志')
    cost_code = relationship('CostCode')

class ContractPaymentNode(Base, TimestampMixin):
    """合同付款节点/收款计划记录表。"""
    __tablename__ = 'mdm_contract_payment_nodes'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    contract_id = Column(Integer, ForeignKey('mdm_revenue_contracts.id'), nullable=False, comment='关联合同ID')
    node_name = Column(String(200), nullable=False, comment='节点名称')
    billing_percentage = Column(Float, comment='收款比例 (%)')
    billing_amount = Column(Float, comment='收款金额')
    linked_system = Column(String(50), comment='关联系统 (gitlab/jira/manual)')
    linked_milestone_id = Column(Integer, comment='关联里程碑ID')
    is_achieved = Column(Boolean, default=False, comment='是否已达成')
    achieved_at = Column(DateTime(timezone=True), comment='达成时间')
    contract = relationship('RevenueContract', back_populates='payment_nodes')

class UserCredential(Base, TimestampMixin):
    """用户凭证表。"""
    __tablename__ = 'sys_user_credentials'
    id = Column(Integer, primary_key=True, autoincrement=True, comment='自增主键')
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), unique=True, comment='用户ID')
    password_hash = Column(String(255), nullable=False, comment='密码哈希值')
    last_login_at = Column(DateTime(timezone=True), nullable=True, comment='最后登录时间')
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
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, Text, DateTime, Date, 
    ForeignKey, Table, JSON, Index, func, UniqueConstraint, Float, select,
    UUID
)
from sqlalchemy.orm import relationship, backref, DeclarativeBase
JSONB = JSON
from sqlalchemy.ext.hybrid import hybrid_property

class Base(DeclarativeBase):
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
    org_id = Column(String(100), nullable=False, index=True)
    org_name = Column(String(200), nullable=False)
    org_level = Column(Integer, default=1)
    parent_org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    parent = relationship("Organization", remote_side=[org_id], backref=backref("children", cascade="all"))
    manager = relationship("User", foreign_keys=[manager_user_id], back_populates="managed_organizations")
    
    users = relationship("User", foreign_keys="User.department_id", primaryjoin="and_(User.department_id==Organization.org_id, User.is_current==True)", back_populates="department")
    products = relationship("Product", back_populates="owner_team")

    def __repr__(self) -> str:
        return f"<Organization(org_id='{self.org_id}', name='{self.org_name}', version={self.sync_version})>"

# 关联表：用户与角色
user_roles = Table(
    'sys_user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('rbac_roles.id'), primary_key=True)
)

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
    
    # Relationships
    department = relationship("Organization", foreign_keys=[department_id], back_populates="users")
    managed_organizations = relationship("Organization", foreign_keys="Organization.manager_user_id", back_populates="manager")
    identities = relationship("IdentityMapping", back_populates="user")
    roles = relationship("Role", secondary=user_roles, backref="users")
    
    # Back-references
    test_cases = relationship("TestCase", back_populates="author")
    requirements = relationship("Requirement", back_populates="author")
    managed_products_as_pm = relationship("Product", back_populates="product_manager")
    project_memberships = relationship("ProjectMember", back_populates="user")

    @property
    def external_usernames(self) -> List[str]:
        return [i.external_username for i in self.identities]

    @property
    def projects(self):
        return [pm.project for pm in self.project_memberships]

    def __repr__(self) -> str:
        return f"<User(name='{self.full_name}', email='{self.primary_email}', version={self.sync_version})>"

class Role(Base):
    """系统角色表 (rbac_roles)。"""
    __tablename__ = 'rbac_roles'
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False) # SYSTEM_ADMIN, PROJECT_LEAD, etc.
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))

class IdentityMapping(Base, TimestampMixin):
    """外部身份映射表。"""
    __tablename__ = 'mdm_identity_mappings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    global_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    source_system = Column(String(50), nullable=False)
    external_user_id = Column(String(100), nullable=False)
    external_username = Column(String(100))
    external_email = Column(String(100))
    user = relationship("User", back_populates="identities")

class Product(Base, TimestampMixin):
    """产品主数据表 (mdm_product)。
    
    在主数据管理 (MDM) 中，产品表字段是标准化产品数据的核心组成部分。
    旨在确保跨系统 (如电商平台、库存管理、营销系统) 的一致性。
    """
    __tablename__ = 'mdm_product'

    # 1. 核心标识
    product_id = Column(String(100), primary_key=True, comment="主键, 唯一, 唯一标识 (如 SOFT-DATAHUB-001)")
    product_code = Column(String(25), nullable=False, index=True, comment="软件代码")
    product_name = Column(String(255), nullable=False, comment="软件标准名称")
    
    # 2. 描述与分类
    product_description = Column(Text, nullable=False, comment="产品特性用途")
    category = Column(String(100), comment="引用分类表，关联产品分类")
    
    # 3. 技术属性
    version_schema = Column(String(50), nullable=False, comment="允许部署的版本范围或版本号")
    specification = Column(JSON, comment="键值对形式存储 {软件名称, 版本, 最小内存}")
    runtime_env = Column(JSON, comment="允许运行的目标环境 (Array)")
    checksum = Column(String(255), comment="发布包的哈希值")
    
    # 4. 生命周期与运维
    lifecycle_status = Column(String(50), default='Active', comment="生命周期状态: Active, End-of-Life")
    repo_url = Column(String(255), comment="源代码仓库地址")
    artifact_path = Column(String(255), comment="产物库路径")
    
    # 5. 归属与人员 (保留 product_manager_id)
    owner_team_id = Column(String(100), ForeignKey('mdm_organizations.org_id'), comment="负责该产品部门的组织ID")
    product_manager_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    
    # Relationships
    owner_team = relationship("Organization", back_populates="products")
    product_manager = relationship("User", back_populates="managed_products_as_pm")
    project_relations = relationship("ProjectProductRelation", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product(code='{self.product_code}', name='{self.product_name}')>"

class ProjectProductRelation(Base, TimestampMixin):
    """项目与产品的多对多关联关系表。
    
    用于支持从产品维度统计项目的投入产出（ROI）。
    支持一个项目服务于多个产品（如中台项目），并配置分摊权重。
    """
    __tablename__ = 'mdm_rel_project_product'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(100), ForeignKey('mdm_projects.project_id'), nullable=False, index=True)
    product_id = Column(String(100), ForeignKey('mdm_product.product_id'), nullable=False, index=True)
    
    # 业务属性
    relation_type = Column(String(50), default='PRIMARY', comment="关系类型: PRIMARY(主产品)/SHARED(共享)/DEPENDENCY(依赖)")
    allocation_ratio = Column(Float, default=1.0, comment="成本/统计分摊权重 (0.0-1.0)")
    
    # 联合唯一约束，防止重复绑定
    __table_args__ = (
        UniqueConstraint('project_id', 'product_id', name='uq_project_product'),
    )

    # Relationships
    project = relationship("ProjectMaster", back_populates="product_relations")
    product = relationship("Product", back_populates="project_relations")

class Service(Base, TimestampMixin):
    """服务目录。"""
    __tablename__ = 'mdm_services'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    tier = Column(String(20))
    description = Column(Text)
    costs = relationship("ResourceCost", back_populates="service")
    
    @property
    def total_cost(self):
        return sum(c.amount for c in self.costs)
    @property
    def investment_roi(self):
        return 10.0 if self.total_cost > 0 else 0.0

class ResourceCost(Base, TimestampMixin):
    """资源成本记录。"""
    __tablename__ = 'stg_mdm_resource_costs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey('mdm_services.id'))
    period = Column(String(20))
    amount = Column(Float, default=0.0)
    cost_item = Column(String(100))
    service = relationship("Service", back_populates="costs")

class MetricDefinition(Base, TimestampMixin):
    __tablename__ = 'mdm_metric_definitions'
    metric_code = Column(String(100), primary_key=True)
    metric_name = Column(String(200), nullable=False)
    domain = Column(String(50), nullable=False)

class SystemRegistry(Base, TimestampMixin):
    __tablename__ = 'mdm_systems_registry'
    system_code = Column(String(50), primary_key=True)
    system_name = Column(String(100), nullable=False)

class EntityTopology(Base):
    __tablename__ = 'mdm_entities_topology'
    id = Column(Integer, primary_key=True)

class SyncLog(Base, TimestampMixin):
    __tablename__ = 'sys_sync_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)

class Location(Base): __tablename__ = 'mdm_locations'; id = Column(Integer, primary_key=True)
class Calendar(Base): __tablename__ = 'mdm_calendar'; id = Column(Integer, primary_key=True)
class RawDataStaging(Base): __tablename__ = 'stg_raw_data'; id = Column(Integer, primary_key=True); source = Column(String(50)); entity_type = Column(String(50)); external_id = Column(String(100)); payload = Column(JSON); schema_version = Column(String(20)); collected_at = Column(DateTime(timezone=True))
class OKRObjective(Base): __tablename__ = 'mdm_okr_objectives'; id = Column(Integer, primary_key=True)
class OKRKeyResult(Base): __tablename__ = 'mdm_okr_key_results'; id = Column(Integer, primary_key=True)
class TraceabilityLink(Base): __tablename__ = 'mdm_traceability_links'; id = Column(Integer, primary_key=True)
class TestExecutionSummary(Base): __tablename__ = 'fct_test_execution_summary'; id = Column(Integer, primary_key=True)
class PerformanceRecord(Base): __tablename__ = 'fct_performance_records'; id = Column(Integer, primary_key=True)
class Incident(Base): __tablename__ = 'mdm_incidents'; id = Column(Integer, primary_key=True)
class UserActivityProfile(Base): __tablename__ = 'fct_user_activity_profiles'; id = Column(BigInteger, primary_key=True)
class ServiceProjectMapping(Base): __tablename__ = 'mdm_service_project_mapping'; id = Column(Integer, primary_key=True)
class SLO(Base): __tablename__ = 'mdm_slo_definitions'; id = Column(Integer, primary_key=True)
class ProjectMaster(Base, TimestampMixin, SCDMixin):
    """项目全生命周期主数据 (mdm_projects)。
    
    用于打通“需求 -> 开发 -> 测试 -> 发布”的交付链条。采用 SCD Type 2 保留历史版本。
    """
    __tablename__ = 'mdm_projects'
    
    # 1. 基础标识 (OneID 穿透)
    project_id = Column(String(100), primary_key=True) # 全局唯一项目 ID (系统码+项目 Key)
    project_name = Column(String(200), nullable=False) # 项目的正式名称
    
    # 2. 分类与状态
    project_type = Column(String(50)) # SPRINT/WATERFALL/RESEARCH
    status = Column(String(50), default='PLAN') # PLAN/DEV/TEST/RELEASED
    is_active = Column(Boolean, default=True) # 是否处于活跃/进行中
    
    # 3. 组织与人员关联 (OneID 穿透)
    pm_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True) # 项目经理
    org_id = Column(String(100), ForeignKey('mdm_organizations.org_id')) # 归属业务线 / 部门
    
    # 4. 时间轴管理
    plan_start_date = Column(Date) # 计划启动日期
    plan_end_date = Column(Date) # 计划交付日期
    actual_start_at = Column(DateTime(timezone=True)) # 实际开始时间
    actual_end_at = Column(DateTime(timezone=True)) # 实际完成时间
    
    # 5. 外部系统与财务关联
    external_id = Column(String(100), unique=True) # 外部系统原生 ID (如 Jira Key)
    system_code = Column(String(50), ForeignKey('mdm_systems_registry.system_code')) # 来源系统编码
    budget_code = Column(String(100)) # 预算关联编码 (用于 CAPEX/OPEX 审计)
    budget_type = Column(String(50)) # 预算类型 (CAPEX 资本化/OPEX 费用化)
    
    lead_repo_id = Column(Integer, nullable=True) # 受理仓库 ID (GitLab Project ID)
    description = Column(Text) # 项目简述 (保留字段)

    # Relationships
    organization = relationship("Organization", foreign_keys=[org_id])
    project_manager = relationship("User", foreign_keys=[pm_user_id])
    source_system = relationship("SystemRegistry")
    gitlab_repos = relationship("Project", back_populates="mdm_project")
    product_relations = relationship("ProjectProductRelation", back_populates="project")

    def __repr__(self) -> str:
        return f"<ProjectMaster(project_id='{self.project_id}', name='{self.project_name}')>"
class ContractPaymentNode(Base): __tablename__ = 'mdm_contract_payment_nodes'; id = Column(Integer, primary_key=True)
class RevenueContract(Base): __tablename__ = 'mdm_revenue_contracts'; id = Column(Integer, primary_key=True)
class PurchaseContract(Base): __tablename__ = 'mdm_purchase_contracts'; id = Column(Integer, primary_key=True)
class UserCredential(Base, TimestampMixin):
    """用户凭证表。"""
    __tablename__ = 'sys_user_credentials'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), unique=True)
    password_hash = Column(String(255), nullable=False)
    user = relationship("User", backref=backref("credential", uselist=False))

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

class Company(Base): __tablename__ = 'mdm_company'; company_id = Column(String(50), primary_key=True)
class Vendor(Base): __tablename__ = 'mdm_vendor'; vendor_code = Column(String(50), primary_key=True)
class EpicMaster(Base): __tablename__ = 'mdm_epic'; id = Column(Integer, primary_key=True)
class ComplianceIssue(Base): __tablename__ = 'mdm_compliance_issues'; id = Column(Integer, primary_key=True)

class RawDataMixin: pass

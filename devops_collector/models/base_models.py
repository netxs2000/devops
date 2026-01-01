"""DevOps Collector 公共模型基类。

本模块定义了所有数据源共享的基础核心模型，包括：
- Base: SQLAlchemy 声明式基类。
- Organization: 组织架构主数据 (MDM)。
- User: 全局身份标识及其属性 (MDM)。
- RBAC System: 基于角色的权限控制模型。
- FinOps & OKR: 财务成本与战略目标追踪模型。

所有插件模型均应通过导入本模块的 `Base` 进行扩展。
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    JSON, BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint, select, and_
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship, backref, foreign
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func

# SQLAlchemy 声明式基类
Base = declarative_base()


class TimestampMixin:
    """时间戳混入类。
    
    为模型添加自动更新的创建和更新时间字段。
    """
    created_at = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), 
        onupdate=lambda: datetime.now(timezone.utc)
    )


class RawDataMixin:
    """原始数据混入类。
    
    用于存储 API 返回的完整原始 JSON 镜像，支持溯源分析。
    """
    raw_data = Column(JSON)


class RawDataStaging(Base):
    """原始数据落盘表 (Staging Layer)。
    
    用于存储未经转换的原始 API 响应内容。支持按需重放、审计以及故障排查。
    配合生命周期管理策略，可定期清理旧数据。
    
    Attributes:
        id (int): 自增主键。
        source (str): 数据源来源 (gitlab, sonarqube, jenkins 等)。
        entity_type (str): 实体类型 (merge_request, project, issue, build 等)。
        external_id (str): 外部系统的唯一标识 (如 MR 的 IID 或项目 ID)。
        payload (dict): 原始 JSON 响应内容。
        schema_version (str): 记录采集时的 Schema 版本，默认为 "1.0"。
        collected_at (datetime): 数据采集时间。
    """
    __tablename__ = 'raw_data_staging'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    external_id = Column(String(100), nullable=False, index=True)
    
    payload = Column(JSON, nullable=False)
    schema_version = Column(String(20), default="1.0", index=True)
    collected_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    __table_args__ = (
        UniqueConstraint(
            'source', 'entity_type', 'external_id', 
            name='idx_source_entity_extid'
        ),
    )


class Organization(Base):
    """组织架构主数据 (mdm_organizations)。
    
    建立全集团的汇报线与成本中心映射，支持指标按部门层级汇总。
    
    Attributes:
        org_id (str): 组织唯一编码 (Global ID, e.g., ORG_FIN_001)。
        org_name (str): 组织/部门名称。
        parent_org_id (str): 父级组织 ID。
        org_level (int): 组织层级 (1-集团, 2-事业部, 3-部门)。
        manager_user_id (UUID): 部门负责人 ID (关联 mdm_identities)。
        cost_center (str): 财务成本中心代码。
        is_deleted (bool): 逻辑删除标记。
        children (List[Organization]): 子组织列表。
        manager (User): 组织负责人对象。
        services (List[Service]): 该组织负责的服务列表。
        projects (List[Project]): 该组织关联的技术项目列表 (由插件注入)。
    """
    __tablename__ = 'mdm_organizations'

    # ---------- 主键与唯一标识 ----------
    # 为支持多版本历史记录，使用自增 surrogate 主键 `id`
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 业务自然键仍保持唯一（当前有效记录），但不再强制唯一约束，以便保存历史
    org_id = Column(String(100), nullable=False)

    # ---------- 基础属性 ----------
    org_name = Column(String(200), nullable=False)
    parent_org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    org_level = Column(Integer)  # 1-Group, 2-BU, 3-Dept
    manager_user_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id')
    )
    cost_center = Column(String(100))  # 财务成本中心代码

    # ---------- SCD Type2 必备字段 ----------
    # 乐观锁版本号（每次更新 +1）
    sync_version = Column(BigInteger, default=1, nullable=False)
    # 软删除标记：True 表示该版本已失效（历史），当前有效记录为 False
    is_deleted = Column(Boolean, default=False, nullable=False)
    # 有效期起止，当前记录的 effective_to 为 NULL 表示仍在生效
    effective_from = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    # 是否为当前最新版本（便于快速查询）
    is_current = Column(Boolean, default=True, nullable=False)

    # ---------- 关系映射 ----------
    # 层级关系（子组织）
    children = relationship(
        "Organization",
        primaryjoin="and_(Organization.org_id==foreign(Organization.parent_org_id), Organization.is_current==True)",
        backref=backref('parent', remote_side=[org_id]),
        foreign_keys=[parent_org_id]
    )

    # 业务关联：服务目录
    services = relationship("Service", back_populates="organization")

    # 负责人关联（双向）
    manager = relationship(
        "User",
        primaryjoin="and_(User.global_user_id==Organization.manager_user_id, User.is_current==True)",
        foreign_keys=[manager_user_id],
        back_populates="managed_organizations",
        post_update=True
    )

    # MDM 聚合关系（补全双向）
    users = relationship(
        "User", 
        primaryjoin="and_(User.department_id==Organization.org_id, User.is_current==True)",
        foreign_keys="[User.department_id]", 
        back_populates="department"
    )
    products = relationship("Product", back_populates="organization")
    okr_objectives = relationship("OKRObjective", back_populates="organization")
    revenue_contracts = relationship("RevenueContract", back_populates="organization")

    # 时间戳（创建/更新）
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<Organization(id='{self.org_id}', name='{self.org_name}')>"


class Location(Base):
    """地理位置主数据 (mdm_location)。
    
    为支持省、市、区县三级层级结构，采用统一地址代码表结构（适配 GB/T 2260 国标）。
    
    Attributes:
        location_id (str): 国家标准行政区划代码 (唯一标识)，如 '110105' (朝阳区)。
        location_name (str): 全称（省/市/区县名称），如 '北京市朝阳区'。
        location_type (str): 层级类型 (province, city, district)。
        parent_id (str): 父级行政区划代码（省级为 NULL）。
        short_name (str): 简称，如 '朝阳'。
        region (str): 经济大区 (如华东, 华南)。
        is_active (bool): 是否启用。
        manager_user_id (UUID): 区域负责人 ID。
        children (List[Location]): 子地域列表。
        manager (User): 区域负责人。
    """
    __tablename__ = 'mdm_location'
    
    location_id = Column(String(6), primary_key=True)
    location_name = Column(String(50), nullable=False)
    location_type = Column(String(20), nullable=False)
    parent_id = Column(String(6), ForeignKey('mdm_location.location_id'))
    short_name = Column(String(20), nullable=False)
    region = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    manager_user_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id')
    )
    
    # 自关联关系
    children = relationship(
        "Location", backref=backref('parent', remote_side=[location_id])
    )
    
    # 关联负责人
    manager = relationship(
        "User", 
        primaryjoin="and_(User.global_user_id==Location.manager_user_id, User.is_current==True)",
        foreign_keys=[manager_user_id]
    )
    
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)
    )
    
    __table_args__ = (
        Index('idx_location_type', location_type),
        Index('idx_location_parent', parent_id),
    )

    def __repr__(self) -> str:
        return f"<Location(id='{self.location_id}', name='{self.location_name}')>"


# --- RBAC Permission System ---

class Role(Base):
    """[RBAC] 角色定义表。
    
    存储系统中定义的所有角色类型。

    Attributes:
        id (int): 自增主键。
        name (str): 角色名称 (e.g. "项目管理员")。
        code (str): 角色唯一编码 (e.g. "PROJECT_ADMIN")。
        description (str): 角色描述。
        permissions (List[RolePermission]): 关联的权限列表。
    """
    __tablename__ = 'rbac_roles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    
    # 关联权限
    permissions = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Role(code='{self.code}', name='{self.name}')>"


class Permission(Base):
    """[RBAC] 权限点定义表。
    
    存储系统中所有的原子权限。

    Attributes:
        id (int): 自增主键。
        code (str): 权限唯一编码 (e.g. "ISSUE_EDIT")。
        description (str): 权限描述。
        category (str): 权限分类 (e.g. "ISSUE", "CODE", "RELEASE")。
    """
    __tablename__ = 'rbac_permissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False)
    description = Column(String(200))
    category = Column(String(50))

    def __repr__(self) -> str:
        return f"<Permission(code='{self.code}', category='{self.category}')>"


class RolePermission(Base):
    """[RBAC] 角色-权限关联表。

    Attributes:
        id (int): 自增主键。
        role_id (int): 关联的角色 ID。
        permission_code (str): 关联的权限编码。
        role (Role): 关联的角色对象。
        permission (Permission): 关联的权限对象。
    """
    __tablename__ = 'rbac_role_permissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey('rbac_roles.id'), nullable=False)
    permission_code = Column(
        String(100), ForeignKey('rbac_permissions.code'), nullable=False
    )
    
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission")
    
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_code', name='uix_role_permission'),
    )


class UserRole(Base):
    """[RBAC] 用户-角色关联表。
    
    Attributes:
        id (int): 自增主键。
        user_id (UUID): 关联的用户 ID (mdm_identities.global_user_id)。
        role_id (int): 关联的角色 ID (rbac_roles.id)。
    """
    __tablename__ = 'rbac_user_roles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('mdm_identities.global_user_id'), 
        nullable=False
    )
    role_id = Column(Integer, ForeignKey('rbac_roles.id'), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uix_user_role'),
    )


class UserOAuthToken(Base):
    """用户第三方 OAuth 令牌存储表。
    
    用于存储用户在 GitLab, Jenkins 等系统的 Access Token，实现“持证办理”模式。

    Attributes:
        id (int): 自增主键。
        user_id (UUID): 关联的用户 ID (mdm_identities.global_user_id)。
        provider (str): 提供商 (gitlab, jenkins)。
        access_token (str): 访问令牌。
        refresh_token (str): 刷新令牌。
        token_type (str): 令牌类型，默认 'Bearer'。
        expires_at (datetime): 过期时间。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
    """
    __tablename__ = 'user_oauth_tokens'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('mdm_identities.global_user_id'),
        nullable=False
    )
    provider = Column(String(50), nullable=False)
    
    access_token = Column(String, nullable=False)
    refresh_token = Column(String)
    token_type = Column(String, default='Bearer')
    
    expires_at = Column(DateTime)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    __table_args__ = (
        UniqueConstraint('user_id', 'provider', name='uix_user_provider'),
    )

    def __repr__(self) -> str:
        return f"<UserOAuthToken(user_id={self.user_id}, provider='{self.provider}')>"


class User(Base):
    """人员主数据 (mdm_identities)。
    
    全局唯一标识，集团级唯一身份 ID (OneID)。
    
    Attributes:
        global_user_id (UUID): 全局唯一标识 (UUID)。
        employee_id (str): 集团 HR 系统工号 (核心锚点)。
        full_name (str): 法律姓名。
        primary_email (str): 集团官方办公邮箱。
        identity_map (dict): 多系统账号映射关系 (JSONB)。
        match_confidence (float): 算法匹配置信度 (0.0-1.0)。
        is_survivor (bool): 是否为当前生效的“生存者”黄金记录。
        is_active (bool): 账号状态 (在职/离职)。
        department_id (str): 所属部门 ID (mdm_organizations.org_id)。
        location_id (str): 所属地理位置 ID (mdm_location.location_id)。
        source_system (str): 标记该“生存者记录”的主来源系统。
        sync_version (int): 乐观锁版本号。
        department (Organization): 所属组织对象。
        location (Location): 所属地域对象。
        managed_organizations (List[Organization]): 该用户管理的组织列表。
        roles (List[Role]): 用户关联的角色列表。
        identities (List[IdentityMapping]): 该用户的多源身份映射。
        credential (UserCredential): 用户登录凭证。
    """
    __tablename__ = 'mdm_identities'
    
    # ---------- 主键 ----------
    # 为支持历史版本，使用自增 surrogate 主键 `id`
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 业务自然键保持唯一（当前有效记录），不再强制唯一约束，以便保存历史
    global_user_id = Column(UUID(as_uuid=True), nullable=False)

    employee_id = Column(String(50))
    full_name = Column(String(200), nullable=False)
    primary_email = Column(String(200))
    
    identity_map = Column(JSONB)
    
    match_confidence = Column(Float)
    is_survivor = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # ---------- SCD Type2 必备字段 ----------
    sync_version = Column(BigInteger, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    effective_from = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)
    )
    
    source_system = Column(String(50))
    
    # 组织与地域属性
    department_id = Column(
        String(100), ForeignKey('mdm_organizations.org_id')
    )
    location_id = Column(
        String(6), ForeignKey('mdm_location.location_id')
    )
    
    # ---------- 关系映射 ----------
    department = relationship(
        "Organization", 
        primaryjoin="and_(Organization.org_id==User.department_id, Organization.is_current==True)",
        foreign_keys=[department_id], 
        back_populates="users"
    )
    location = relationship("Location", foreign_keys=[location_id])
    
    # [RBAC] 管理的组织 (作为负责人)
    managed_organizations = relationship(
        "Organization", 
        primaryjoin="and_(Organization.manager_user_id==User.global_user_id, Organization.is_current==True)",
        back_populates="manager", 
        foreign_keys="[Organization.manager_user_id]"
    )
    
    # [RBAC] 关联角色
    roles = relationship("Role", secondary="rbac_user_roles", backref="users")
    identities = relationship(
        "IdentityMapping", back_populates="user", cascade="all, delete-orphan"
    )
    
    # Association Proxies (黑科技 1)
    # 直接获取用户在所有三方系统中的用户名列表
    external_usernames = association_proxy('identities', 'external_username')
    # 直接获取用户在所有系统中绑定的外部ID列表
    external_ids = association_proxy('identities', 'external_user_id')
    
    # 业务画像与目标补全 (双向)
    activity_profiles = relationship("UserActivityProfile", back_populates="user", cascade="all, delete-orphan")
    okr_objectives = relationship("OKRObjective", back_populates="owner")
    test_cases = relationship("TestCase", back_populates="author")
    requirements = relationship("Requirement", back_populates="author")
    
    # 多重角色产品管理关系
    managed_products_as_pm = relationship("Product", foreign_keys="[Product.product_manager_id]", back_populates="product_manager")
    managed_products_as_dm = relationship("Product", foreign_keys="[Product.dev_manager_id]", back_populates="dev_manager")
    managed_products_as_tm = relationship("Product", foreign_keys="[Product.test_manager_id]", back_populates="test_manager")
    managed_products_as_rm = relationship("Product", foreign_keys="[Product.release_manager_id]", back_populates="release_manager")
    
    # 插件数据直达 (Association Proxies)
    project_memberships = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")
    projects = association_proxy('project_memberships', 'project')
    
    __table_args__ = (
        Index('idx_identity_map', identity_map, postgresql_using='gin'),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.global_user_id}, name='{self.full_name}')>"


class LaborRateConfig(Base, TimestampMixin):
    """人工费率配置模型 (Labor Rate Configuration)。

    用于定义不同岗位级别、不同区域或不同组织的“标准人天成本 (Blended Rate)”。

    Attributes:
        id (int): 自增内部主键。
        job_title_level (str): 岗位序列与级别 (如 P7, Senior)。
        organization_id (str): 关联的组织 ID (可选)。
        daily_rate (float): 标准人天成本金额。
        hourly_rate (float): 标准人时成本金额。
        currency (str): 币种代码 (如 CNY, USD)。
        effective_date (datetime): 费率生效时间。
        is_active (bool): 是否启用该费率配置。
        organization (Organization): 关联的 Organization 对象。
    """
    __tablename__ = 'labor_rate_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_title_level = Column(String(100), nullable=False, index=True)
    organization_id = Column(
        String(100), ForeignKey('mdm_organizations.org_id'), nullable=True
    )
    
    daily_rate = Column(Float, nullable=False)
    hourly_rate = Column(Float)
    currency = Column(String(10), default='CNY')
    
    effective_date = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_active = Column(Boolean, default=True)
    
    organization = relationship(
        "Organization", 
        primaryjoin="and_(Organization.org_id==LaborRateConfig.organization_id, Organization.is_current==True)"
    )

    def __repr__(self) -> str:
        return f"<LaborRateConfig(level='{self.job_title_level}', rate={self.daily_rate})>"


class IdentityMapping(Base):
    """身份映射关系表 (mdm_identity_mappings)。
    
    存储 OneID 到各子系统的具体账号 ID。
    
    Attributes:
        id (int): 自增主键。
        global_user_id (UUID): 关联的全局 OneID。
        source_system (str): 子系统标识 (gitlab, jira, feishu 等)。
        external_user_id (str): 在子系统中的唯一标识 (如 GitLab 内部 User ID)。
        external_username (str): 子系统中的用户名。
        external_email (str): 子系统中的邮箱。
        mapping_type (str): 映射类型 (manual, automatic)。
        last_seen_at (datetime): 最近一次在该系统发现该账号的时间。
        user (User): 关联的 User 对象。
    """
    __tablename__ = 'mdm_identity_mappings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    global_user_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id')
    )
    
    source_system = Column(String(50), nullable=False)
    external_user_id = Column(String(100), nullable=False)
    external_username = Column(String(100))
    external_email = Column(String(200))
    
    mapping_type = Column(String(20), default='automatic') # manual, automatic
    last_seen_at = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="identities")
    
    __table_args__ = (
        UniqueConstraint(
            'source_system', 'external_user_id', name='uix_source_extid'
        ),
        Index('idx_mapping_user', global_user_id),
    )

    def __repr__(self) -> str:
        return f"<IdentityMapping(system='{self.source_system}', ext_id='{self.external_user_id}')>"


class SyncLog(Base):
    """同步任务执行日志模型。
    
    记录采集器每次同步的执行状态与统计信息。
    
    Attributes:
        id (int): 自增主键。
        source (str): 数据源 (gitlab, jira 等)。
        entity_type (str): 同步实体类型 (projects, issues 等)。
        status (str): 状态 (running, success, failed)。
        started_at (datetime): 开始时间。
        finished_at (datetime): 结束时间。
        records_processed (int): 处理总记录数。
        records_created (int): 新增记录数。
        records_updated (int): 更新记录数。
        records_failed (int): 失败记录数。
        error_message (str): 异常信息摘要。
    """
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), index=True)
    entity_type = Column(String(50), index=True)
    status = Column(String(20)) # running, success, failed
    
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    
    error_message = Column(Text)

    def __repr__(self) -> str:
        return f"<SyncLog(id={self.id}, source='{self.source}', status='{self.status}')>"


class ProjectSyncControl(Base, TimestampMixin):
    """项目级同步增量控制表。
    
    存储每个项目各实体的上次同步标记 (Checkpoints)，实现断点续传。
    
    Attributes:
        id (int): 自增主键。
        project_id (int): 关联的仓库/项目 ID。
        entity_type (str): 同步实体类型 (commits, merge_requests 等)。
        last_sync_time (datetime): 上次同步成功的时间。
        last_sync_cursor (str): 上次同步游标 (如 commit sha 或 offsetID)。
        is_active (bool): 该同步任务是否启用。
    """
    __tablename__ = 'project_sync_controls'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    
    last_sync_time = Column(DateTime(timezone=True))
    last_sync_cursor = Column(String(255))
    
    is_active = Column(Boolean, default=True)
    
    __table_args__ = (
        UniqueConstraint(
            'project_id', 'entity_type', name='uix_proj_entity'
        ),
    )

    def __repr__(self) -> str:
        return f"<ProjectSyncControl(project_id={self.project_id}, entity='{self.entity_type}')>"


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
    organization_id = Column(
        String(100), ForeignKey('mdm_organizations.org_id')
    )
    finance_code = Column(String(100))  # 关联财务系统的预算科目或项目代码
    
    # 关联的技术项目 ID (由具体插件定义意义)
    project_id = Column(Integer)
    
    # 外部关联 (Jira/ZenTao)
    external_epic_id = Column(String(100))  # 关联外部 Epic ID
    external_goal_id = Column(String(100))  # 关联外部 Goal/Objective ID
    source_system = Column(String(50))      # zentao, jira
    
    # 角色负责人 (关联到全局 User)
    # 角色负责人 (关联到全局 User)
    product_manager_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id')
    )
    dev_manager_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id')
    )
    test_manager_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id')
    )
    release_manager_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id')
    )
    
    # 关系
    children = relationship("Product", backref=backref('parent', remote_side=[id]))
    organization = relationship(
        "Organization", 
        primaryjoin="and_(Organization.org_id==Product.organization_id, Organization.is_current==True)",
        back_populates="products"
    )
    
    product_manager = relationship("User", primaryjoin="and_(User.global_user_id==Product.product_manager_id, User.is_current==True)", foreign_keys=[product_manager_id], back_populates="managed_products_as_pm")
    dev_manager = relationship("User", primaryjoin="and_(User.global_user_id==Product.dev_manager_id, User.is_current==True)", foreign_keys=[dev_manager_id], back_populates="managed_products_as_dm")
    test_manager = relationship("User", primaryjoin="and_(User.global_user_id==Product.test_manager_id, User.is_current==True)", foreign_keys=[test_manager_id], back_populates="managed_products_as_tm")
    release_manager = relationship("User", primaryjoin="and_(User.global_user_id==Product.release_manager_id, User.is_current==True)", foreign_keys=[release_manager_id], back_populates="managed_products_as_rm")
    
    # 财务与合同 (双向)
    revenue_contracts = relationship("RevenueContract", back_populates="product")
    
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
    owner = relationship("User", primaryjoin="and_(User.global_user_id==OKRObjective.owner_id, User.is_current==True)", back_populates="okr_objectives")
    organization = relationship(
        "Organization", 
        primaryjoin="and_(Organization.org_id==OKRObjective.organization_id, Organization.is_current==True)",
        back_populates="okr_objectives"
    )
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
    organization = relationship(
        "Organization", 
        primaryjoin="and_(Organization.org_id==Service.organization_id, Organization.is_current==True)",
        back_populates="services"
    )
    product = relationship("Product")
    slos = relationship("SLO", back_populates="service", cascade="all, delete-orphan")
    projects = relationship("ServiceProjectMapping", back_populates="service", cascade="all, delete-orphan")
    resource_costs = relationship("ResourceCost", back_populates="service")

    # ROI & 健康度评估 (黑科技 3 & 4)
    @hybrid_property
    def total_cost(self):
        """服务的累计投入成本 (ROI 基准)。"""
        return sum(c.amount for c in self.resource_costs)

    @total_cost.expression
    def total_cost(cls):
        """服务的累计投入成本 SQL 聚合。"""
        return select(func.sum(ResourceCost.amount)).\
            where(ResourceCost.service_id == cls.id).\
            label("total_cost")

    @hybrid_property
    def health_score(self):
        """服务的综合健康度评分 (0-100)。
        目前的逻辑是基于 SLO 达成率的简单模拟，生产中可与 Project 关联。
        """
        # 简单示例逻辑：基于关联项目的活跃度或质量 (此处由 SLO 数量模拟)
        if not self.slos: return 80.0
        return 100.0 - (len(self.slos) * 2)

    @hybrid_property
    def investment_roi(self):
        """投入产出比 (ROI)。
        公式：健康度分值 / (累计投入 / 10000)
        用于衡量每万元投入带来的稳定性/质量收益。
        """
        cost = self.total_cost
        if not cost or cost == 0: return 0.0
        return round(self.health_score / (cost / 10000.0), 2)


class ServiceProjectMapping(Base, TimestampMixin):
    """服务与技术项目映射表。
    
    解决一个逻辑服务对应多个代码仓库/项目的问题。

    Attributes:
        id: 自增主键。
        service_id: 关联的服务 ID。
        source: 数据源 (gitlab 等)。
        project_id: 项目 ID。
        service: 关联的服务对象。
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
    """测试执行汇总记录模型 (test_execution_summaries)。
    
    聚合单次构建或测试任务的全量结果，支持测试金字塔分层分析。
    
    Attributes:
        id (int): 自增主键。
        project_id (int): 关联的 GitLab 项目 ID。
        build_id (str): 关联的 Jenkins Build ID 或外部 Job ID。
        test_level (str): 测试层级 (Unit, API, UI, Integration, Performance)。
        test_tool (str): 使用的测试工具 (pytest, jmeter, selenium 等)。
        total_cases (int): 总测试用例数。
        passed_count (int): 通过数。
        failed_count (int): 失败数。
        skipped_count (int): 跳过数。
        pass_rate (float): 通过率百分比。
        duration_ms (int): 执行总耗时 (毫秒)。
        raw_data (dict): 原始 JSON 备份。
    """
    __tablename__ = 'test_execution_summaries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer)
    build_id = Column(String(100))
    
    test_level = Column(String(50), nullable=False) 
    test_tool = Column(String(50))
    
    total_cases = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    pass_rate = Column(Float)
    duration_ms = Column(BigInteger)
    
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<TestExecutionSummary(build_id='{self.build_id}', level='{self.test_level}')>"


class PerformanceRecord(Base):
    """性能/压力测试指标记录模型。
    
    Attributes:
        id (int): 自增主键。
        project_id (int): 关联项目 ID。
        build_id (str): 关联构建 ID。
        scenario_name (str): 压测场景或接口名。
        avg_latency (float): 平均耗时 (ms)。
        p99_latency (float): P99 耗时 (ms)。
        throughput (float): 吞吐量 (TPS/RPS)。
        error_rate (float): 错误率 (%)。
        concurrency (int): 并发用户数。
        raw_data (dict): 原始 JSON。
    """
    __tablename__ = 'performance_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer)
    build_id = Column(String(100))
    
    scenario_name = Column(String(200), nullable=False)
    
    # 核心性能指标
    avg_latency = Column(Float)
    p99_latency = Column(Float)
    throughput = Column(Float)
    error_rate = Column(Float)
    
    concurrency = Column(Integer)
    
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<PerformanceRecord(scenario='{self.scenario_name}', build='{self.build_id}')>"


class Incident(Base, TimestampMixin):
    """运维事故/故障记录模型。
    
    用于计算 MTTR (平均恢复时间) 和变更失败率。
    
    Attributes:
        id (int): 自增主键。
        external_id (str): 外部系统 ID (如 JIRA-999)。
        source_system (str): 来源系统 (jira, zentao, pagerduty, prometheus)。
        title (str): 事故标题。
        description (str): 事故详细描述。
        severity (str): 严重等级 (P0, P1, P2, P3)。
        status (str): 处理状态 (investigating, resolved, closed)。
        occurred_at (datetime): 发现时间。
        resolved_at (datetime): 恢复时间。
        mttr_seconds (int): 恢复耗时 (秒)。
        project_id (int): 关联的 GitLab 项目 ID。
        related_deployment_id (int): 关联的可能导致故障的部署 ID。
        related_change_sha (str): 关联的可能导致故障的提交 SHA。
        root_cause_type (str): 根因分类 (CodeBug, Infra 等)。
        impact_scope (str): 影响范围描述。
        raw_data (dict): 原始 JSON 数据。
    """
    __tablename__ = 'incidents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(100), unique=True)
    source_system = Column(String(50))
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    severity = Column(String(20))
    status = Column(String(20))
    
    occurred_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    mttr_seconds = Column(Integer)
    
    project_id = Column(Integer)
    related_deployment_id = Column(Integer)
    related_change_sha = Column(String(100))
    
    root_cause_type = Column(String(50))
    impact_scope = Column(String(200))
    
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<Incident(id='{self.external_id}', status='{self.status}')>"


class CostCode(Base, TimestampMixin):
    """成本分解结构模型 (Cost Breakdown Structure - CBS Tree)。

    用于建立独立于行政组织的财务核算体系。

    Attributes:
        id (int): 自增内部主键。
        code (str): 财务科目编码 (唯一，如 1002.01.03)。
        name (str): 科目显示名称。
        description (str): 科目说明。
        parent_id (int): 父级科目 ID。
        category (str): 成本大类 (Labor, Cloud, License, Infrastructure)。
        default_capex_opex (str): 默认支出性质 (CAPEX, OPEX)。
        is_active (bool): 状态标记。
        costs (List[ResourceCost]): 关联的成本流水。
    """
    __tablename__ = 'cost_codes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 树形结构
    parent_id = Column(Integer, ForeignKey('cost_codes.id'))
    children = relationship("CostCode", backref=backref('parent', remote_side=[id]))
    
    category = Column(String(50))
    default_capex_opex = Column(String(20))
    is_active = Column(Boolean, default=True)
    
    costs = relationship("ResourceCost", back_populates="cost_code")
    purchase_contracts = relationship("PurchaseContract", back_populates="cost_code")

    def __repr__(self) -> str:
        return f"<CostCode(code='{self.code}', name='{self.name}')>"


class ResourceCost(Base, TimestampMixin):
    """资源与成本流水模型。
    
    记录各项支出的明细。
    
    Attributes:
        id (int): 自增主键。
        project_id (int): 关联的项目 ID。
        product_id (int): 关联的产品 ID。
        organization_id (str): 关联的组织 ID。
        period (str): 统计周期 (2025-01)。
        cost_type (str): 成本类型 (Infrastructure, HumanLabor 等)。
        cost_item (str): 具体成本项。
        cost_code_id (int): 关联的财务科目 ID。
        purchase_contract_id (int): 关联的采购合同 ID。
        amount (float): 金额。
        currency (str): 币种。
        capex_opex_flag (str): 支出性质。
        is_locked (bool): 是否已关账。
        source_system (str): 来源系统。
        raw_data (dict): 原始数据备份。
        cost_code (CostCode): 关联的科目对象。
        purchase_contract (PurchaseContract): 关联的合同对象。
    """
    __tablename__ = 'resource_costs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    project_id = Column(Integer)
    product_id = Column(Integer)
    organization_id = Column(String(100))
    
    period = Column(String(50), nullable=False)
    
    cost_type = Column(String(50))
    cost_item = Column(String(100))
    
    cost_code_id = Column(Integer, ForeignKey('cost_codes.id'))
    purchase_contract_id = Column(Integer, ForeignKey('purchase_contracts.id'))
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='CNY')
    
    capex_opex_flag = Column(String(20))
    is_locked = Column(Boolean, default=False)
    accounting_date = Column(DateTime(timezone=True))
    
    source_system = Column(String(50))
    description = Column(Text)
    raw_data = Column(JSON)
    
    cost_code = relationship("CostCode", back_populates="costs")
    purchase_contract = relationship("PurchaseContract", back_populates="costs")
    
    # 关联到逻辑服务
    service_id = Column(Integer, ForeignKey('services.id'))
    service = relationship("Service", back_populates="resource_costs")

    def __repr__(self) -> str:
        return f"<ResourceCost(id={self.id}, item='{self.cost_item}', amount={self.amount})>"


class UserActivityProfile(Base, TimestampMixin):
    """用户行为画像模型。
    
    Attributes:
        id (int): 自增主键。
        user_id (UUID): 用户 ID (mdm_identities.global_user_id)。
        period (str): 统计周期。
        avg_review_turnaround (float): 平均评审响应时长 (秒)。
        review_participation_rate (float): 评审参与率。
        context_switch_rate (float): 任务切换频率。
        top_languages (dict): 主要语言分布。
        off_hours_activity_ratio (float): 非工作时间活动占比。
        avg_lint_errors_per_kloc (float): 千行代码 Lint 错误。
        code_review_acceptance_rate (float): 评审通过率。
        user (User): 关联的用户对象。
    """
    __tablename__ = 'user_activity_profiles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('mdm_identities.global_user_id'),
        nullable=False
    )
    period = Column(String(50), nullable=False)
    
    avg_review_turnaround = Column(Float)
    review_participation_rate = Column(Float)
    
    context_switch_rate = Column(Float)
    contribution_diversity = Column(Float)
    
    top_languages = Column(JSON)
    
    off_hours_activity_ratio = Column(Float)
    weekend_activity_count = Column(Integer)
    
    avg_lint_errors_per_kloc = Column(Float)
    code_review_acceptance_rate = Column(Float)
    
    user = relationship(
        "User", 
        primaryjoin="and_(User.global_user_id==UserActivityProfile.user_id, User.is_current==True)",
        back_populates="activity_profiles"
    )
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<UserActivityProfile(user_id={self.user_id}, period='{self.period}')>"


class RevenueContract(Base, TimestampMixin):
    """收入合同模型 (Revenue Contract)。
 
    记录业务端签署的产生外部收入的合同。

    Attributes:
        id (int): 自增内部主键。
        contract_no (str): 外部合同唯一编号。
        title (str): 合同名称。
        client_name (str): 客户名称。
        total_value (float): 合同总金额。
        currency (str): 币种 (默认 CNY)。
        sign_date (datetime): 签署日期。
        product_id (int): 关联的产品 ID。
        organization_id (str): 负责交付的组织 ID。
        status (str): 合同状态 (Active, Finished, Suspended)。
        product (Product): 关联的产品模型。
        organization (Organization): 关联的组织模型。
        payment_nodes (List[ContractPaymentNode]): 关联的回款节点。
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
    
    product = relationship("Product", back_populates="revenue_contracts")
    organization = relationship(
        "Organization", 
        primaryjoin="and_(Organization.org_id==RevenueContract.organization_id, Organization.is_current==True)",
        back_populates="revenue_contracts"
    )
    payment_nodes = relationship("ContractPaymentNode", back_populates="contract", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<RevenueContract(id={self.id}, no='{self.contract_no}')>"


class ContractPaymentNode(Base, TimestampMixin):
    """合同回款节点/里程碑模型。

    Attributes:
        id (int): 自增主键。
        contract_id (int): 所属合同 ID。
        node_name (str): 节点名称。
        billing_amount (float): 应收金额。
        linked_milestone_id (int): 关联的外部里程碑 ID。
        is_achieved (bool): 技术指标是否已达成。
        is_billed (bool): 是否已开票/回款。
        contract (RevenueContract): 关联的合同对象。
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

    def __repr__(self) -> str:
        return f"<ContractPaymentNode(id={self.id}, name='{self.node_name}')>"


class PurchaseContract(Base, TimestampMixin):
    """采购合同模型 (Purchase Contract)。

    Attributes:
        id (int): 自增主键。
        contract_no (str): 合同编号。
        vendor_name (str): 供应商名称。
        total_amount (float): 总金额。
        cost_code_id (int): 关联的财务科目 ID。
        status (str): 合同状态。
        cost_code (CostCode): 关联的科目对象。
        costs (List[ResourceCost]): 关联的成本流水。
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
    cost_code = relationship("CostCode", back_populates="purchase_contracts")
    costs = relationship("ResourceCost", back_populates="purchase_contract")

    def __repr__(self) -> str:
        return f"<PurchaseContract(id={self.id}, vendor='{self.vendor_name}')>"


class UserCredential(Base, TimestampMixin):
    """用户凭证存储模型 (mdm_credentials)。
    
    Attributes:
        user_id (UUID): 关联的全局用户 ID (mdm_identities.global_user_id)。
        password_hash (str): 密码哈希。
        last_login_at (datetime): 最后登录时间。
        user (User): 关联的用户对象。
    """
    __tablename__ = 'mdm_credentials'
    
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('mdm_identities.global_user_id'), 
        primary_key=True
    )
    password_hash = Column(String(200), nullable=False)
    last_login_at = Column(DateTime(timezone=True))
    
    user = relationship(
        "User", 
        primaryjoin="and_(User.global_user_id==UserCredential.user_id, User.is_current==True)",
        backref=backref(
            "credential", uselist=False, cascade="all, delete-orphan",
            primaryjoin="and_(User.global_user_id==foreign(UserCredential.user_id), User.is_current==True)"
        )
    )

    def __repr__(self) -> str:
        return f"<UserCredential(user_id={self.user_id})>"

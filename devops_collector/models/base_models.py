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
    
    聚合来自各个系统（GitLab, Jira, ZenTao等）的人员信息。
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
    """身份映射表，记录不同系统的账号归属。"""
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
    """同步日志模型，记录每次同步任务的执行结果。"""
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
    
    用于在业务层面聚合技术项目和负责人。
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
    
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


# 公共辅助类
class TimestampMixin:
    """时间戳混入类，为模型添加创建和更新时间。"""
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


class RawDataMixin:
    """原始数据混入类，存储 API 返回的完整 JSON。"""
    raw_data = Column(JSON)

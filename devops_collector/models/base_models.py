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
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
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
    # 注意：这里不直接定义 relationship，而是在各插件的 User 模型中通过 back_populates 建立
    # 这样可以避免循环导入问题
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


class User(Base):
    """用户模型，支持 GitLab 用户和虚拟用户。
    
    采用全局自增 ID 作为主键，`gitlab_id` 为可空字段，
    支持手动录入外部贡献者 (无 GitLab 账号)。
    
    Attributes:
        id: 系统内部全局 ID (自增主键)
        gitlab_id: 原始 GitLab 用户 ID (虚拟用户为 NULL)
        is_virtual: 是否为虚拟/外部用户
        department: 部门名称 (从 skype/skypi 字段提取)
        organization_id: 关联的组织架构 ID
        
    Note:
        - organization relationship 在各插件中通过 back_populates 定义
        - 这样可以避免循环导入问题
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    gitlab_id = Column(Integer, unique=True, nullable=True)  # NULL for virtual users
    
    username = Column(String(100))
    name = Column(String(200))
    email = Column(String(200))
    public_email = Column(String(200))
    state = Column(String(20))  # active, blocked
    
    # 部门信息
    department = Column(String(100))
    is_virtual = Column(Boolean, default=False)
    
    # 关联组织
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    # organization relationship 在插件中定义
    
    # 额外信息
    avatar_url = Column(String(500))
    web_url = Column(String(500))
    
    # 原始数据
    raw_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SyncLog(Base):
    """同步日志模型，记录每次同步任务的执行结果。
    
    Attributes:
        source: 数据源类型 ('gitlab', 'sonarqube')
        project_id: 关联项目 ID (根据来源不同指向不同表)
        project_key: 项目标识 (SonarQube 使用)
        status: 任务结果 ('SUCCESS', 'FAILED')
        message: 详细信息或错误堆栈
        timestamp: 记录时间
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


# 公共辅助类
class TimestampMixin:
    """时间戳混入类，为模型添加创建和更新时间。"""
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))


class RawDataMixin:
    """原始数据混入类，存储 API 返回的完整 JSON。"""
    raw_data = Column(JSON)

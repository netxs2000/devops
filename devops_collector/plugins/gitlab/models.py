"""GitLab Data Collector - 数据模型定义

本模块定义了 GitLab 特定的 SQLAlchemy ORM 模型，用于持久化 GitLab 数据到 PostgreSQL。
包含项目、提交、流水线、部署、合并请求、议题、评论等实体。

公共模型（Base, Organization, User, SyncLog）从 base_models 导入。

Typical usage:
    from devops_collector.plugins.gitlab.models import Project, Commit
    
    session.add(Project(id=1, name="MyProject"))
    session.commit()
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone

# 从公共基础模型导入 Base 和共享模型
from devops_collector.models.base_models import Base, Organization, User, SyncLog

# 为 Organization 和 User 添加 GitLab 插件特定的关系
# 注意：这些关系在 base_models 中未定义，以避免循环依赖
Organization.users = relationship("User", back_populates="organization")
Organization.projects = relationship("Project", back_populates="organization")
User.organization = relationship("Organization", back_populates="users")


class Project(Base):
    """GitLab 项目模型，存储项目元数据和同步状态。
    
    核心功能：
        - 存储项目基本信息 (名称、描述、路径)
        - 跟踪同步状态和断点续传信息
        - 记录项目指标 (Star、Fork、Issue 数量)
    
    Attributes:
        id: GitLab 项目 ID (主键，与 GitLab 保持一致)
        name: 项目名称
        sync_status: 同步状态 ('PENDING', 'SYNCING', 'FAILED', 'COMPLETED')
        sync_state: 断点续传状态 JSON (如 {"commits_page": 5})
        department: 归属部门 (从顶级群组描述映射)
    """
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)  # GitLab Project ID
    name = Column(String)
    path_with_namespace = Column(String)
    description = Column(String)
    department = Column(String) # Mapped from Top-level Group description
    created_at = Column(DateTime(timezone=True))
    last_activity_at = Column(DateTime(timezone=True))
    
    # Sync status
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String, default='PENDING') # PENDING, SYNCING, FAILED, COMPLETED
    
    raw_data = Column(JSON) # Store full JSON response
    
    # Resumable sync state (e.g. {"commits_page": 5, "issues_page": 2})
    sync_state = Column(JSON, default={})
    
    # Project Capacity (Storage Size in Bytes)
    storage_size = Column(BigInteger)

    # Metrics
    star_count = Column(Integer)
    forks_count = Column(Integer)
    open_issues_count = Column(Integer)
    
    commit_count = Column(Integer)
    tags_count = Column(Integer)
    branches_count = Column(Integer)
    
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    organization = relationship("Organization", back_populates="projects")

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class MergeRequest(Base):
    """合并请求 (MR) 模型。
    
    Attributes:
        id: GitLab MR ID
        iid: 项目内 MR 编号 (如 !123)
        author_id: 发起人 ID (关联 User.id)
        state: MR 状态 ('opened', 'merged', 'closed')
        merged_at: 合并时间 (用于 DORA 指标计算)
    """
    __tablename__ = 'merge_requests'
    
    id = Column(Integer, primary_key=True) # GitLab MR ID
    iid = Column(Integer) # Project Internal ID
    project_id = Column(Integer, ForeignKey('projects.id'))
    title = Column(String)
    description = Column(String)
    state = Column(String) # opened, closed, merged, locked
    author_username = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    merged_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    
    reviewers = Column(JSON)
    changes_count = Column(String) # sometimes "10+"
    diff_refs = Column(JSON)
    
    raw_data = Column(JSON)
    
    author_id = Column(Integer, ForeignKey('users.id'))
    author = relationship("User")
    
    project = relationship("Project")

class Commit(Base):
    """代码提交记录模型。
    
    采用复合主键 (id + project_id) 支持同一 Commit 在不同 Fork 项目中出现。
    
    Attributes:
        id: Commit SHA 哈希值
        project_id: 关联项目 ID
        author_name/email: 作者信息 (用于身份匹配)
        committed_date: 提交时间 (用于活动分析)
        gitlab_user_id: 关联的 GitLab 用户 ID (由 IdentityMatcher 填充)
    """
    __tablename__ = 'commits'
    
    id = Column(String, primary_key=True) # sha
    project_id = Column(Integer, ForeignKey('projects.id'), primary_key=True)
    short_id = Column(String)
    title = Column(String)
    author_name = Column(String)
    author_email = Column(String)
    authored_date = Column(DateTime(timezone=True))
    committed_date = Column(DateTime(timezone=True))
    message = Column(String)
    
    # Git Stats
    additions = Column(Integer)
    deletions = Column(Integer)
    total = Column(Integer)

    raw_data = Column(JSON)
    
    gitlab_user_id = Column(Integer, ForeignKey('users.id'))
    author_user = relationship("User")
    
    project = relationship("Project")

class CommitFileStats(Base):
    """提交文件级别统计模型，区分代码/注释/空行。
    
    用于精细化代码贡献分析，过滤 "import 注释行" 等脱水数据。
    
    Attributes:
        file_path: 文件路径
        language: 推断的编程语言
        code_added/deleted: 有效代码行数
        comment_added/deleted: 注释行数
        blank_added/deleted: 空行数
    """
    __tablename__ = 'commit_file_stats'
    
    id = Column(Integer, primary_key=True)
    commit_id = Column(String, ForeignKey('commits.id'))
    file_path = Column(String)
    language = Column(String)
    
    code_added = Column(Integer, default=0)
    code_deleted = Column(Integer, default=0)
    comment_added = Column(Integer, default=0)
    comment_deleted = Column(Integer, default=0)
    blank_added = Column(Integer, default=0)
    blank_deleted = Column(Integer, default=0)
    
    commit = relationship("Commit")

class Issue(Base):
    """议题 (Issue) 模型，存储需求、缺陷、任务等工作项。
    
    Attributes:
        iid: 项目内 Issue 编号 (如 #456)
        author_id: 发起人 ID
        time_estimate: 预估工时 (秒)
        total_time_spent: 实际花费工时 (秒)
        labels: 标签列表 (JSON)
    """
    __tablename__ = 'issues'
    
    id = Column(Integer, primary_key=True) # GitLab Issue Internal ID
    iid = Column(Integer) # Project specific Issue ID
    project_id = Column(Integer, ForeignKey('projects.id'))
    title = Column(String)
    description = Column(String)
    state = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    
    # Time Tracking
    time_estimate = Column(Integer) # in seconds
    total_time_spent = Column(Integer) # in seconds
    labels = Column(JSON) # List of label strings
    
    raw_data = Column(JSON)
    
    author_id = Column(Integer, ForeignKey('users.id'))
    author = relationship("User")
    
    project = relationship("Project")


class Pipeline(Base):
    """流水线 (CI/CD Pipeline) 模型。
    
    用于 DORA 指标计算 (部署频率、变更失败率)。
    
    Attributes:
        status: 流水线状态 ('success', 'failed', 'running'...)
        duration: 执行时长 (秒)
        coverage: 代码覆盖率
        failure_reason: 失败原因
    """
    __tablename__ = 'pipelines'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    status = Column(String)
    ref = Column(String)
    sha = Column(String)
    source = Column(String)
    duration = Column(Integer) # in seconds
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    coverage = Column(String) # "98.5"
    failure_reason = Column(String)
    
    raw_data = Column(JSON)
    
    project = relationship("Project")

class Deployment(Base):
    """部署记录模型，DORA 指标核心数据源。
    
    Attributes:
        environment: 部署环境 ('production', 'staging'...)
        status: 部署状态 ('success', 'failed')
        ref: 部署分支/Tag
        sha: 部署的 Commit SHA
    """
    __tablename__ = 'deployments'
    
    id = Column(Integer, primary_key=True)
    iid = Column(Integer)
    project_id = Column(Integer, ForeignKey('projects.id'))
    status = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    ref = Column(String)
    sha = Column(String)
    environment = Column(String)
    
    raw_data = Column(JSON)
    
    project = relationship("Project")

class Note(Base):
    """评论/笔记模型，存储 Issue 和 MR 上的讨论内容。
    
    用于代码评审分析 (Code Review Impact)。
    
    Attributes:
        noteable_type: 关联对象类型 ('Issue' 或 'MergeRequest')
        noteable_iid: 关联对象 ID
        body: 评论内容
        system: 是否为系统自动生成的消息
        resolvable: 是否可解决 (用于 Code Review 统计)
    """
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    noteable_type = Column(String) # Issue, MergeRequest
    noteable_iid = Column(Integer) 
    body = Column(String)
    author_id = Column(Integer) # Link to User.id manually if needed
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    system = Column(Boolean)
    resolvable = Column(Boolean)
    
    raw_data = Column(JSON)
    
    project = relationship("Project")


class Tag(Base):
    """标签/版本号模型，用于 Release 分析。
    
    Attributes:
        name: 标签名称 (如 v1.0.0)
        message: 标签签名消息
        commit_sha: 关联的 Commit SHA
        created_at: 创建时间 (通常与 Commit 时间相同)
    """
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    name = Column(String)
    message = Column(String)
    commit_sha = Column(String) # Linking to Commit info
    created_at = Column(DateTime(timezone=True)) # Usually from commit.committed_date if tag date invalid
    
    project = relationship("Project")

class Branch(Base):
    """分支模型，存储项目的 Git 分支信息。
    
    用于分支活跃度分析和僵尸分支识别。
    
    Attributes:
        name: 分支名称 (如 main, develop)
        last_commit_sha: 最新 Commit SHA
        last_commit_date: 最近提交时间 (代理创建时间)
        last_committer_name: 最近提交人 (代理创建人)
        is_merged/is_protected/is_default: 分支状态标志
    """
    __tablename__ = 'branches'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    name = Column(String)
    
    # Head Commit Info
    last_commit_sha = Column(String)
    last_commit_date = Column(DateTime(timezone=True)) 
    last_committer_name = Column(String)
    
    is_merged = Column(Boolean)
    is_protected = Column(Boolean)
    is_default = Column(Boolean)
    
    raw_data = Column(JSON)
    
    project = relationship("Project")

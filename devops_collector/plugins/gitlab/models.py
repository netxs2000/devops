"""GitLab 插件数据模型模块。

本模块定义了从 GitLab 同步的所有核心实体，包括群组、项目、合并请求、
提交记录、Issue 以及 CI/CD 流水线等。这些模型与 SQLAlchemy ORM 配合使用，
支持自动化的数据映射和复杂的关联查询。

Typical Usage:
    session.query(GitLabGroup).filter(GitLabGroup.path == 'my-group').first()
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, BigInteger, Text
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from datetime import datetime, timezone

# 从公共基础模型导入 Base 和共享模型
from devops_collector.models.base_models import Base, Organization, User, SyncLog

# 为 Organization 和 User 添加 GitLab 插件特定的关系
Organization.users = relationship("User", back_populates="organization")
Organization.projects = relationship("Project", back_populates="organization")
User.organization = relationship("Organization", back_populates="users")

class GitLabGroup(Base):
    """GitLab 群组模型。
    
    代表 GitLab 中的顶级或子群组，支持树形嵌套结构。
    
    Attributes:
        id: 群组在 GitLab 系统中的唯一标识 ID。
        name: 群组名称。
        path: 群组路径。
        full_path: 群组全路径，作为唯一约束键。
        description: 群组描述。
        parent_id: 父群组 ID，用于构建树形结构。
        visibility: 可见性级别 (public, internal, private)。
        avatar_url: 头像链接。
        web_url: Web 查看链接。
        created_at: GitLab 上的创建时间。
        updated_at: GitLab 上的最后更新时间。
        children: 子群组列表。
        projects: 属于该群组的项目列表。
        raw_data: 存储 API 返回的原始 JSON。
        members: 该群组的成员列表。
    """
    __tablename__ = 'gitlab_groups'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    path = Column(String(255))
    full_path = Column(String(500), unique=True)
    description = Column(Text)
    
    parent_id = Column(Integer, ForeignKey('gitlab_groups.id'))
    
    visibility = Column(String(20))
    avatar_url = Column(String(500))
    web_url = Column(String(500))
    
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    children = relationship("GitLabGroup", backref=backref('parent', remote_side=[id]))
    projects = relationship("Project", back_populates="group")
    raw_data = Column(JSON)
    members = relationship("GitLabGroupMember", back_populates="group", cascade="all, delete-orphan")


class GitLabGroupMember(Base):
    """GitLab 群组成员模型。
    
    维护用户与群组之间的多对多关联及权限信息。
    
    Attributes:
        id: 数据库自增 ID。
        group_id: 关联的群组 ID。
        user_id: 关联的系统内部用户 ID。
        gitlab_uid: 该用户在 GitLab 中的 UID。
        access_level: 权限等级 (如 Guest, Developer, Maintainer, Owner)。
        state: 成员状态。
        joined_at: 加入群组的时间。
        expires_at: 权限过期时间。
        group: 关联的群组对象。
        user: 关联的用户对象。
    """
    __tablename__ = 'gitlab_group_members'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('gitlab_groups.id'))
    user_id = Column(Integer, ForeignKey('users.id')) 
    gitlab_uid = Column(Integer)
    access_level = Column(Integer) 
    state = Column(String(20)) 
    joined_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    
    group = relationship("GitLabGroup", back_populates="members")
    user = relationship("User")


class Project(Base):
    """GitLab 项目模型。
    
    存储 GitLab 中项目的元数据，并关联到组织架构。
    
    Attributes:
        group_id: 所属群组 ID。
        group: 关联的 GitLabGroup 对象。
        id: 项目在 GitLab 系统中的唯一标识 ID。
        name: 项目名称。
        path_with_namespace: 项目带命名空间的完整路径。
        description: 项目描述。
        department: 业务归属部门（手动映射或业务逻辑定义）。
        created_at: GitLab 上的创建时间。
        last_activity_at: 最后活跃时间。
        last_synced_at: 系统上次成功同步该项目数据的时间。
        sync_status: 当前同步状态 (PENDING, SYNCING, SUCCESS, FAILED)。
        raw_data: API 返回的原始 JSON 信息。
        sync_state: 存储增量同步的游标或状态信息。
        storage_size: 项目占用的存储空间大小 (bytes)。
        star_count: Star 数量。
        forks_count: Fork 数量。
        open_issues_count: 开启状态的 Issue 数量。
        commit_count: 提交总数。
        tags_count: 标签(Tag)总数。
        branches_count: 分支总数。
        organization_id: 关联的组织架构 ID。
        organization: 关联的 Organization 对象。
        updated_at: 数据库记录的最后更新时间。
        milestones: 项目关联的里程碑列表。
    """
    __tablename__ = 'projects'
    
    group_id = Column(Integer, ForeignKey('gitlab_groups.id'))
    group = relationship("GitLabGroup", back_populates="projects")

    id = Column(Integer, primary_key=True) 
    name = Column(String)
    path_with_namespace = Column(String)
    description = Column(String)
    department = Column(String) 
    created_at = Column(DateTime(timezone=True))
    last_activity_at = Column(DateTime(timezone=True))
    
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String, default='PENDING') 
    raw_data = Column(JSON) 
    sync_state = Column(JSON, default={})
    storage_size = Column(BigInteger)

    star_count = Column(Integer)
    forks_count = Column(Integer)
    open_issues_count = Column(Integer)
    
    commit_count = Column(Integer)
    tags_count = Column(Integer)
    branches_count = Column(Integer)
    
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    organization = relationship("Organization", back_populates="projects")

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")


class MergeRequest(Base):
    """合并请求 (MR) 模型。
    
    存储代码合并请求的核心数据及其在 DevOps 生命周期中的协作元数据。
    
    Attributes:
        id: MR 在 GitLab 中的唯一内部 ID。
        iid: MR 在项目内的 IID。
        project_id: 所属项目 ID。
        title: MR 标题。
        description: MR 详细描述。
        state: MR 状态 (opened, closed, merged)。
        author_username: 作者用户名。
        created_at: 创建时间。
        updated_at: 更新时间。
        merged_at: 合并时间。
        closed_at: 关闭时间。
        reviewers: 评审人列表 (JSON 存储)。
        changes_count: 变更文件数量。
        diff_refs: 差异参考信息 (SHA 等)。
        merge_commit_sha: 合并后的 Commit SHA。
        raw_data: 原始 JSON。
        external_issue_id: 关联的外部需求 ID (如 Jira)。
        issue_source: 需求来源系统 (jira, zentao)。
        first_response_at: 首次评审回复时间。
        review_cycles: 评审轮次，用于衡量协作效率。
        human_comment_count: 人工评论数量。
        approval_count: 审批通过的人数。
        review_time_total: 从创建到合并的总评审时长 (秒)。
        quality_gate_status: 质量门禁状态 (passed, failed)。
        author_id: 关联的系统内部用户 ID。
        author: 关联的 User 对象。
        project: 关联的 Project 对象。
    """
    __tablename__ = 'merge_requests'
    
    id = Column(Integer, primary_key=True) 
    iid = Column(Integer) 
    project_id = Column(Integer, ForeignKey('projects.id'))
    title = Column(String)
    description = Column(String)
    state = Column(String) 
    author_username = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    merged_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    
    reviewers = Column(JSON)
    changes_count = Column(String) 
    diff_refs = Column(JSON)
    
    merge_commit_sha = Column(String)
    raw_data = Column(JSON)
    
    # 链路追溯：关联外部业务需求 (Jira/ZenTao)
    external_issue_id = Column(String(100))
    issue_source = Column(String(50)) # jira, zentao

    # 协作行为元数据 (Developer Experience)
    first_response_at = Column(DateTime(timezone=True)) # 首次评审回复时间
    review_cycles = Column(Integer, default=1)           # 评审轮次 (修订次数)
    human_comment_count = Column(Integer, default=0)    # 人工评论数 (排除系统消息)
    approval_count = Column(Integer, default=0)         # 审批通过人数
    review_time_total = Column(BigInteger)               # 总评审耗时 (秒)
    
    # 规范遵循度
    quality_gate_status = Column(String(20)) # passed, failed
    
    author_id = Column(Integer, ForeignKey('users.id'))
    author = relationship("User")
    
    project = relationship("Project")


class Commit(Base):
    """代码提交记录模型。
    
    存储代码库的每一次提交信息，并关联需求和规范检查状态。
    
    Attributes:
        id: Commit 的完整 SHA 标识。
        project_id: 所属项目 ID。
        short_id: Commit 的短 SHA。
        title: 提交标题。
        author_name: 作者名称。
        author_email: 作者邮箱。
        authored_date: 作者签名时间。
        committed_date: 提交时间（写入 Git 库的时间）。
        message: 完整的提交说明。
        additions: 新增行数。
        deletions: 删除行数。
        total: 总变更行数。
        raw_data: 原始 JSON。
        linked_issue_ids: 关联的需求 ID 列表 (JSON)。
        issue_source: 需求来源系统。
        is_off_hours: 是否在非工作时间提交。
        lint_status: 代码规范检查状态。
        gitlab_user_id: 关联的系统内部用户 ID。
        author_user: 关联的 User 对象。
        project: 关联的 Project 对象。
    """
    __tablename__ = 'commits'
    
    id = Column(String, primary_key=True) 
    project_id = Column(Integer, ForeignKey('projects.id'), primary_key=True)
    short_id = Column(String)
    title = Column(String)
    author_name = Column(String)
    author_email = Column(String)
    authored_date = Column(DateTime(timezone=True))
    committed_date = Column(DateTime(timezone=True))
    message = Column(String)
    
    additions = Column(Integer)
    deletions = Column(Integer)
    total = Column(Integer)

    raw_data = Column(JSON)
    
    # 链路追溯：支持从提交说明中提取的多个需求 ID
    linked_issue_ids = Column(JSON) # 存储为数组，如 ["PROJ-123", "PROJ-456"]
    issue_source = Column(String(50)) # jira, zentao
    
    # 行为特征：加班与规范
    is_off_hours = Column(Boolean, default=False) # 是否为非工作时间提交
    lint_status = Column(String(20))               # passed, failed, warning
    
    gitlab_user_id = Column(Integer, ForeignKey('users.id'))
    author_user = relationship("User")
    
    project = relationship("Project")


class CommitFileStats(Base):
    """提交文件级别统计模型。
    
    用于细粒度分析每次提交中不同类型文件的代码量和注释率。
    
    Attributes:
        id: 自增主键。
        commit_id: 关联的 Commit ID。
        file_path: 文件路径。
        language: 编程语言。
        file_type_category: 文件类型分类 (Code, Test, IaC, Config)。
        code_added: 新增代码行数。
        code_deleted: 删除代码行数。
        comment_added: 新增注释行数。
        comment_deleted: 删除注释行数。
        blank_added: 新增空行数。
        blank_deleted: 删除空行数。
        commit: 关联的 Commit 对象。
    """
    __tablename__ = 'commit_file_stats'
    
    id = Column(Integer, primary_key=True)
    commit_id = Column(String, ForeignKey('commits.id'))
    file_path = Column(String)
    language = Column(String)
    file_type_category = Column(String(50)) # Code, Test, IaC, Config
    
    code_added = Column(Integer, default=0)
    code_deleted = Column(Integer, default=0)
    comment_added = Column(Integer, default=0)
    comment_deleted = Column(Integer, default=0)
    blank_added = Column(Integer, default=0)
    blank_deleted = Column(Integer, default=0)
    
    commit = relationship("Commit")


class Issue(Base):
    """议题 (Issue) 模型。
    
    代表项目中的任务、缺陷或需求。
    
    Attributes:
        id: Issue 在 GitLab 中的唯一内部 ID。
        iid: 项目内 IID。
        project_id: 所属项目 ID。
        title: 标题。
        description: 描述。
        state: 状态 (opened, closed)。
        created_at: 创建时间。
        updated_at: 更新时间。
        closed_at: 关闭时间。
        time_estimate: 预估耗时 (秒)。
        total_time_spent: 实际累计耗时 (秒)。
        labels: 标签列表 (JSON)。
        raw_data: 原始 JSON。
        author_id: 关联的系统内部用户 ID。
        author: 关联的 User 对象。
        project: 关联的 Project 对象。
        events: 关联的状态变更事件流。
    """
    __tablename__ = 'issues'
    
    id = Column(Integer, primary_key=True) 
    iid = Column(Integer) 
    project_id = Column(Integer, ForeignKey('projects.id'))
    title = Column(String)
    description = Column(String)
    state = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    
    time_estimate = Column(Integer) 
    total_time_spent = Column(Integer) 
    labels = Column(JSON) 
    
    raw_data = Column(JSON)
    
    author_id = Column(Integer, ForeignKey('users.id'))
    author = relationship("User")
    
    project = relationship("Project")
    events = relationship("GitLabIssueEvent", back_populates="issue", cascade="all, delete-orphan")


class GitLabIssueEvent(Base):
    """GitLab Issue 变更事件流。
    
    CALMS 扫描核心表，用于根据事件流重建 Issue 的状态演进过程（如前置时间计算）。
    
    Attributes:
        id: 自增主键。
        issue_id: 关联的 Issue ID。
        user_id: 触发该事件的用户 ID。
        event_type: 事件类型 (state, label, milestone, iteration)。
        action: 动作类型 (add, remove, closed, reopened, update)。
        external_event_id: GitLab 侧的原始 Event ID。
        meta_info: 存储具体的变更内容（如标签名、状态值等）。
        created_at: 事件发生时间。
        issue: 关联的 Issue 对象。
        user: 关联的 User 对象。
    """
    __tablename__ = 'gitlab_issue_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey('issues.id'))
    user_id = Column(Integer, ForeignKey('users.id')) 
    event_type = Column(String(50))   # state, label, milestone, iteration
    action = Column(String(50))       # add, remove, closed, reopened, update
    external_event_id = Column(Integer) # GitLab 原始 event id
    meta_info = Column(JSON)          # 存储具体的标签名、状态、里程碑等
    created_at = Column(DateTime(timezone=True)) 

    issue = relationship("Issue", back_populates="events")
    user = relationship("User")


class Pipeline(Base):
    """流水线 (CI/CD Pipeline) 模型。
    
    记录 CI/CD 执行的结果、时长和覆盖率等工程效能核心指标。
    
    Attributes:
        id: 流水线在 GitLab 中的唯一 ID。
        project_id: 所属项目 ID。
        status: 状态 (success, failed, canceled, skipped)。
        ref: 分支或标签。
        sha: 触发流水线的 Commit SHA。
        source: 触发源 (push, web, schedule 等)。
        duration: 执行总时长 (秒)。
        created_at: 创建时间。
        updated_at: 最后更新时间。
        coverage: 测试覆盖率。
        failure_reason: 失败原因。
        raw_data: 原始 JSON。
        project: 关联的 Project 对象。
    """
    __tablename__ = 'pipelines'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    status = Column(String)
    ref = Column(String)
    sha = Column(String)
    source = Column(String)
    duration = Column(Integer) 
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    coverage = Column(String) 
    failure_reason = Column(String)
    
    raw_data = Column(JSON)
    
    project = relationship("Project")


class Deployment(Base):
    """部署记录模型。
    
    记录代码被部署到不同环境的执行结果及其追踪 SHA。
    
    Attributes:
        id: 部署在 GitLab 中的唯一内部 ID。
        iid: 项目内 IID。
        project_id: 所属项目 ID。
        status: 部署状态 (created, running, success, failed, canceled)。
        created_at: 创建时间。
        updated_at: 更新时间。
        ref: 部署的分支或标签。
        sha: 部署的 Commit SHA。
        environment: 部署环境名称 (如 production, staging)。
        raw_data: 原始 JSON。
        project: 关联的 Project 对象。
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
    """评论/笔记模型。
    
    存储 Issue、MR 等对象下的讨论内容和系统通知。
    
    Attributes:
        id: Note 在 GitLab 中的唯一 ID。
        project_id: 所属项目 ID。
        noteable_type: 被评论的对象类型 (MergeRequest, Issue, Commit)。
        noteable_iid: 被评论对象的 IID。
        body: 评论的正文内容。
        author_id: 评论者在 GitLab 侧的 UID (或映射后的 user_id)。
        created_at: 评论创建时间。
        updated_at: 评论更新时间。
        system: 是否为系统产生的评论及通知。
        resolvable: 是否为可解决的评价。
        raw_data: 原始 JSON。
        project: 关联的 Project 对象。
    """
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    noteable_type = Column(String) 
    noteable_iid = Column(Integer) 
    body = Column(String)
    author_id = Column(Integer) 
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    system = Column(Boolean)
    resolvable = Column(Boolean)
    
    raw_data = Column(JSON)
    
    project = relationship("Project")


class Tag(Base):
    """标签/版本号模型。
    
    Attributes:
        id: 数据库自增 ID。
        project_id: 所属项目 ID。
        name: 标签名称。
        message: 标签消息。
        commit_sha: 对应的 Commit SHA。
        created_at: 创建时间。
        project: 关联的 Project 对象。
    """
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    name = Column(String)
    message = Column(String)
    commit_sha = Column(String) 
    created_at = Column(DateTime(timezone=True)) 
    
    project = relationship("Project")


class Branch(Base):
    """分支模型。
    
    Attributes:
        id: 数据库自增 ID。
        project_id: 所属项目 ID。
        name: 分支名称。
        last_commit_sha: 最后一次提交的 SHA。
        last_commit_date: 最后一次提交的时间。
        last_committer_name: 最后一次提交的作者。
        is_merged: 是否已合并。
        is_protected: 是否为保护分支。
        is_default: 是否为默认分支。
        raw_data: 原始 JSON。
        project: 关联的 Project 对象。
    """
    __tablename__ = 'branches'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    name = Column(String)
    
    last_commit_sha = Column(String)
    last_commit_date = Column(DateTime(timezone=True)) 
    last_committer_name = Column(String)
    
    is_merged = Column(Boolean)
    is_protected = Column(Boolean)
    is_default = Column(Boolean)
    
    raw_data = Column(JSON)
    
    project = relationship("Project")

class Milestone(Base):
    """里程碑模型。
    
    Attributes:
        id: GitLab Milestone 的全局唯一 ID。
        iid: 项目内 IID。
        project_id: 所属项目 ID。
        title: 里程碑标题。
        description: 描述内容。
        state: 状态 (active, closed)。
        due_date: 截止日期。
        start_date: 开始日期。
        created_at: 创建时间。
        updated_at: 更新时间。
        raw_data: 原始 JSON。
        project: 关联的 Project 对象。
    """
    __tablename__ = 'milestones'
    
    id = Column(Integer, primary_key=True) # GitLab Milestone ID
    iid = Column(Integer)
    project_id = Column(Integer, ForeignKey('projects.id'))
    title = Column(String)
    description = Column(String)
    state = Column(String) # active, closed
    
    due_date = Column(DateTime(timezone=True))
    start_date = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    
    raw_data = Column(JSON)
    
    project = relationship("Project", back_populates="milestones")


class GitLabPackage(Base):
    """GitLab 制品库包模型。
    
    Attributes:
        id: GitLab Package ID。
        project_id: 所属项目 ID。
        name: 包名。
        version: 版本号。
        package_type: 包类型 (maven, npm, pypi等)。
        status: 状态。
        created_at: 创建时间。
        web_url: Web 链接。
        project: 关联的 Project 对象。
        files: 该包包含的文件。
        raw_data: 原始 JSON。
    """
    __tablename__ = 'gitlab_packages'
    
    id = Column(Integer, primary_key=True) # GitLab Package ID
    project_id = Column(Integer, ForeignKey('projects.id'))
    
    name = Column(String(255), nullable=False)
    version = Column(String(100))
    package_type = Column(String(50)) # maven, npm, pypi, etc.
    status = Column(String(50)) # default, hidden, processing, etc.
    
    created_at = Column(DateTime(timezone=True))
    
    web_url = Column(String(500))
    
    project = relationship("Project")
    files = relationship("GitLabPackageFile", back_populates="package", cascade="all, delete-orphan")
    raw_data = Column(JSON)


class GitLabPackageFile(Base):
    """GitLab 包关联的文件模型。
    
    Attributes:
        id: GitLab Package File ID。
        package_id: 关联的包 ID。
        file_name: 文件名。
        size: 文件大小 (bytes)。
        file_sha1: SHA1 校验值。
        file_sha256: SHA256 校验值。
        created_at: 创建时间。
        package: 关联的 GitLabPackage 对象。
        raw_data: 原始 JSON。
    """
    __tablename__ = 'gitlab_package_files'
    
    id = Column(Integer, primary_key=True) # GitLab Package File ID
    package_id = Column(Integer, ForeignKey('gitlab_packages.id'))
    
    file_name = Column(String(255), nullable=False)
    size = Column(BigInteger)
    file_sha1 = Column(String(40))
    file_sha256 = Column(String(64))
    
    created_at = Column(DateTime(timezone=True))
    
    package = relationship("GitLabPackage", back_populates="files")
    raw_data = Column(JSON)


class GitLabWikiLog(Base):
    """GitLab Wiki 变更日志模型。
    
    Attributes:
        id: 自增主键。
        project_id: 所属项目 ID。
        title: Wiki 页面标题。
        slug: Wiki 页面路径。
        format: 文档格式。
        action: 变更动作 (created, updated, deleted)。
        user_id: 操作者 ID。
        created_at: 操作时间。
        project: 关联的项目对象。
        user: 关联的用户对象。
        raw_data: 原始 JSON。
    """
    __tablename__ = 'gitlab_wiki_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    title = Column(String(255))
    slug = Column(String(255))
    format = Column(String(20))
    action = Column(String(50)) # created, updated, deleted
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True))
    
    project = relationship("Project")
    user = relationship("User")
    raw_data = Column(JSON)


class GitLabDependency(Base):
    """GitLab 项目依赖模型。
    
    Attributes:
        id: 自增主键。
        project_id: 所属项目 ID。
        name: 依赖包名。
        version: 依赖版本。
        package_manager: 包管理器 (maven, npm 等)。
        dependency_type: 依赖类型 (direct, transitive)。
        project: 关联的项目对象。
        raw_data: 原始 JSON。
    """
    __tablename__ = 'gitlab_dependencies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    name = Column(String(255), nullable=False)
    version = Column(String(100))
    package_manager = Column(String(50)) # maven, npm, pip, etc.
    dependency_type = Column(String(50)) # direct, transitive
    
    project = relationship("Project")
    raw_data = Column(JSON)

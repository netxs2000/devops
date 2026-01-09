"""GitLab 插件数据模型模块。

本模块定义了从 GitLab 同步的所有核心实体，包括群组、项目、合并请求、
提交记录、Issue 以及 CI/CD 流水线等。这些模型与 SQLAlchemy ORM 配合使用，
支持自动化的数据映射和复杂的关联查询。

所有模型均继承自 `devops_collector.models.base_models.Base`。

典型用法:
    >>> from devops_collector.plugins.gitlab.models import GitLabGroup
    >>> session.query(GitLabGroup).filter(GitLabGroup.path == 'my-group').first()
"""
from datetime import datetime, timezone
from typing import List, Optional
from devops_collector.config import settings
from sqlalchemy import JSON, BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, select, cast, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from devops_collector.models.base_models import Base, Organization, User, SyncLog
Organization.gitlab_projects = relationship('GitLabProject', back_populates='organization')

class GitLabGroup(Base):
    """GitLab 群组模型。
    
    代表 GitLab 中的顶级或子群组，支持树形嵌套结构。
    
    Attributes:
        id (int): 群组在 GitLab 系统中的唯一标识 ID。
        name (str): 群组名称。
        path (str): 群组路径。
        full_path (str): 群组全路径，作为唯一约束键。
        description (str): 群组描述。
        parent_id (int): 父群组 ID，用于构建树形结构。
        visibility (str): 可见性级别 (public, internal, private)。
        avatar_url (str): 头像链接。
        web_url (str): Web 查看链接。
        created_at (datetime): GitLab 上的创建时间。
        updated_at (datetime): GitLab 上的最后更新时间。
        children (List[GitLabGroup]): 子群组列表。
        projects (List[Project]): 属于该群组的项目列表。
        raw_data (dict): 存储 API 返回的原始 JSON。
        members (List[GitLabGroupMember]): 该群组的成员列表。
    """
    __tablename__ = 'gitlab_groups'
    __table_args__ = {'extend_existing': True}
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
    children = relationship('GitLabGroup', backref=backref('parent', remote_side=[id]))
    projects = relationship('GitLabProject', back_populates='group')
    raw_data = Column(JSON)
    members = relationship('GitLabGroupMember', back_populates='group', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        """GitLabGroup 字符串表示。"""
        return f"<GitLabGroup(id={self.id}, full_path='{self.full_path}')>"

class GitLabGroupMember(Base):
    """GitLab 群组成员模型。
    
    维护用户与群组之间的多对多关联及权限信息。
    
    Attributes:
        id (int): 数据库自增 ID。
        group_id (int): 关联的群组 ID。
        user_id (UUID): 关联的系统内部用户 ID (mdm_identities.global_user_id)。
        gitlab_uid (int): 该用户在 GitLab 中的 UID。
        access_level (int): 权限等级 (10=Guest, 20=Reporter, 30=Developer, 40=Maintainer, 50=Owner)。
        state (str): 成员状态 (active, invited)。
        joined_at (datetime): 加入群组的时间。
        expires_at (datetime): 权限过期时间。
        group (GitLabGroup): 关联的群组对象。
        user (User): 关联的系统全局用户对象。
    """
    __tablename__ = 'gitlab_group_members'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('gitlab_groups.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    gitlab_uid = Column(Integer)
    access_level = Column(Integer)
    state = Column(String(20))
    joined_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    group = relationship('GitLabGroup', back_populates='members')
    user = relationship('User', primaryjoin='and_(User.global_user_id==GitLabGroupMember.user_id, User.is_current==True)')

    def __repr__(self) -> str:
        return f'<GitLabGroupMember(group_id={self.group_id}, gitlab_uid={self.gitlab_uid})>'

class GitLabProject(Base):
    """GitLab 项目模型。
    
    存储 GitLab 中项目的元数据，并关联到组织架构。
    
    Attributes:
        id (int): 项目在 GitLab 系统中的唯一标识 ID。
        name (str): 项目名称。
        path_with_namespace (str): 项目带命名空间的完整路径。
        description (str): 项目描述。
        department (str): 业务归属部门（手动映射或业务逻辑定义）。
        group_id (int): 所属群组 ID。
        group (GitLabGroup): 关联的 GitLabGroup 对象。
        created_at (datetime): GitLab 上的创建时间。
        last_activity_at (datetime): 最后活跃时间。
        last_synced_at (datetime): 系统上次成功同步该项目数据的时间。
        sync_status (str): 当前同步状态 (PENDING, SYNCING, SUCCESS, FAILED)。
        raw_data (dict): API 返回的原始 JSON 信息。
        sync_state (dict): 存储增量同步的游标或状态信息。
        storage_size (int): 项目占用的存储空间大小 (bytes)。
        star_count (int): Star 数量。
        forks_count (int): Fork 数量。
        open_issues_count (int): 开启状态的 Issue 数量。
        commit_count (int): 提交总数。
        tags_count (int): 标签(Tag)总数。
        branches_count (int): 分支总数。
        organization_id (str): 关联的组织架构 ID (mdm_organizations.org_id)。
        organization (Organization): 关联的 Organization 对象。
        mdm_project_id (int): 关联的主项目 ID (mdm_projects.id)。
        mdm_project (ProjectMaster): 关联的主项目对象。
        updated_at (datetime): 数据库记录的最后更新时间。
        milestones (List[Milestone]): 项目关联的里程碑列表。
        members (List[GitLabProjectMember]): 项目成员列表。
    """
    __tablename__ = 'gitlab_projects'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    name = Column(String)
    path_with_namespace = Column(String)
    description = Column(String)
    department = Column(String)
    group_id = Column(Integer, ForeignKey('gitlab_groups.id'))
    group = relationship('GitLabGroup', back_populates='projects')
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
    organization_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    organization = relationship('Organization', primaryjoin='and_(Organization.org_id==GitLabProject.organization_id, Organization.is_current==True)', back_populates='gitlab_projects')
    mdm_project_id = Column(String(100), ForeignKey('mdm_projects.project_id'), nullable=True)
    from devops_collector.models.base_models import ProjectMaster
    mdm_project = relationship('ProjectMaster', back_populates='gitlab_repos')
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    dependency_scans = relationship('DependencyScan', back_populates='project', cascade='all, delete-orphan')
    dependencies = relationship('Dependency', back_populates='project', cascade='all, delete-orphan')
    milestones = relationship('GitLabMilestone', back_populates='project', cascade='all, delete-orphan')
    members = relationship('GitLabProjectMember', back_populates='project', cascade='all, delete-orphan')
    commits = relationship('GitLabCommit', back_populates='project', cascade='all, delete-orphan')
    merge_requests = relationship('GitLabMergeRequest', back_populates='project', cascade='all, delete-orphan')
    issues = relationship('GitLabIssue', back_populates='project', cascade='all, delete-orphan')
    pipelines = relationship('GitLabPipeline', back_populates='project', cascade='all, delete-orphan')
    deployments = relationship('GitLabDeployment', back_populates='project', cascade='all, delete-orphan')
    # Add relationships for other modules and plugins
    test_cases = relationship('GTMTestCase', back_populates='project', cascade='all, delete-orphan')
    requirements = relationship('GTMRequirement', back_populates='project', cascade='all, delete-orphan')
    test_execution_records = relationship('GTMTestExecutionRecord', back_populates='project', cascade='all, delete-orphan')
    sonar_projects = relationship('SonarProject', back_populates='gitlab_project')
    jira_projects = relationship('JiraProject', back_populates='gitlab_project')

    @hybrid_property
    def visibility(self):
        """项目可见性 (public, internal, private)。"""
        return self.raw_data.get('visibility') if self.raw_data else None

    @hybrid_property
    def web_url(self):
        """项目的 GitLab 网页地址。"""
        return self.raw_data.get('web_url') if self.raw_data else None

    @hybrid_property
    def is_archived(self):
        """项目是否已归档。"""
        return self.raw_data.get('archived', False) if self.raw_data else False

    @is_archived.expression
    def is_archived(cls):
        '''"""TODO: Add description.

Args:
    cls: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return func.coalesce(func.json_extract(cls.raw_data, '$.archived'), False)

    @hybrid_property
    def mttr(self):
        """平均恢复时长 (MTTR) - 单位: 秒。"""
        incidents = [i for i in self.issues if i.is_incident and i.state == 'closed']
        if not incidents:
            return 0.0
        r_times = [i.resolution_time for i in incidents if i.resolution_time is not None]
        return sum(r_times) / len(r_times) if r_times else 0.0

    @mttr.expression
    def mttr(cls):
        """MTTR 的 SQL 聚合。"""
        Issue_ = cls.issues.property.mapper.class_
        return select(func.avg(Issue_.resolution_time)).where(Issue_.project_id == cls.id).where(Issue_.is_incident == True).where(Issue_.state == 'closed').scalar_subquery()

    @hybrid_property
    def change_failure_rate(self):
        """变更失败率 (CFR) - 单位: 百分比。
        计算公式：(变更失败 Issues 数 / 成功部署数) * 100
        """
        success_deploys = len([d for d in self.deployments if d.is_success])
        if success_deploys == 0:
            return 0.0
        failures = len([i for i in self.issues if i.is_change_failure])
        return failures / success_deploys * 100

    @change_failure_rate.expression
    def change_failure_rate(cls):
        """CFR 的 SQL 聚合。"""
        from sqlalchemy import case, cast, Float
        Issue_ = cls.issues.property.mapper.class_
        Deployment_ = cls.deployments.property.mapper.class_
        failures_count = select(func.count(Issue_.id)).where(Issue_.project_id == cls.id).where(Issue_.is_change_failure == True).scalar_subquery()
        deploy_count = select(func.count(Deployment_.id)).where(Deployment_.project_id == cls.id).where(Deployment_.status == 'success').scalar_subquery()
        return case((deploy_count > 0, cast(failures_count, Float) / cast(deploy_count, Float) * 100), else_=0.0)

    def __repr__(self) -> str:
        return f"<GitLabProject(id={self.id}, path='{self.path_with_namespace}')>"

class GitLabProjectMember(Base):
    """GitLab 项目成员模型 (Project Level RBAC)。
    
    用于在更细粒度（项目级）控制用户权限。
    
    Attributes:
        id (int): 自增主键。
        project_id (int): 关联的项目 ID。
        user_id (UUID): 关联的系统内部用户 ID (mdm_identities.global_user_id)。
        gitlab_uid (int): GitLab 用户 ID。
        access_level (int): 权限等级 (10=Guest, 20=Reporter, 30=Developer, 40=Maintainer, 50=Owner)。
        role_id (int): 关联的系统角色 ID (rbac_roles.id)。
        role (Role): 关联的 Role 对象。
        job_title (str): 成员在项目中的具体角色（如 "Frontend Lead"）。
        joined_at (datetime): 加入时间。
        expires_at (datetime): 权限过期时间。
        project (Project): 关联的 Project 对象。
        user (User): 关联的 User 对象。
    """
    __tablename__ = 'gitlab_project_members'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    gitlab_uid = Column(Integer)
    access_level = Column(Integer)
    role_id = Column(Integer, ForeignKey('rbac_roles.id'), nullable=True)
    role = relationship('Role')
    job_title = Column(String(100))
    joined_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    project = relationship('GitLabProject', back_populates='members')
    user = relationship('User', primaryjoin='and_(User.global_user_id==GitLabProjectMember.user_id, User.is_current==True)', back_populates='project_memberships')

    def __repr__(self) -> str:
        return f'<GitLabProjectMember(project_id={self.project_id}, user_id={self.user_id})>'

class GitLabMergeRequest(Base):
    """合并请求 (MR) 模型。
    
    存储代码合并请求的核心数据及其在 DevOps 生命周期中的协作元数据。
    
    Attributes:
        id (int): MR 在 GitLab 中的唯一内部 ID。
        iid (int): MR 在项目内的 IID。
        project_id (int): 所属项目 ID。
        title (str): MR 标题。
        description (str): MR 详细描述。
        state (str): MR 状态 (opened, closed, merged)。
        author_username (str): 作者用户名。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
        merged_at (datetime): 合并时间。
        closed_at (datetime): 关闭时间。
        reviewers (dict): 评审人列表 (JSON 存储)。
        changes_count (str): 变更文件数量。
        diff_refs (dict): 差异参考信息 (SHA 等)。
        merge_commit_sha (str): 合并后的 Commit SHA。
        external_issue_id (str): 关联的外部需求 ID (如 Jira)。
        issue_source (str): 需求来源系统 (jira, zentao)。
        first_response_at (datetime): 首次评审回复时间。
        review_cycles (int): 评审轮次，用于衡量协作效率。
        human_comment_count (int): 人工评论数量。
        approval_count (int): 审批通过的人数。
        review_time_total (int): 从创建到合并的总评审时长 (秒)。
        quality_gate_status (str): 质量门禁状态 (passed, failed)。
        ai_category (str): AI 分类结果 (Feature, Bugfix, etc.)。
        ai_summary (str): AI 生成的业务价值摘要。
        ai_confidence (float): AI 分类置信度。
        author_id (UUID): 关联的系统内部用户 ID (mdm_identities.global_user_id)。
        author (User): 关联的 User 对象。
        project (Project): 关联的 Project 对象。
        raw_data (dict): 原始 JSON 镜像存档。
    """
    __tablename__ = 'gitlab_merge_requests'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    iid = Column(Integer)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
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
    deployments = relationship('GitLabDeployment', primaryjoin='and_(GitLabMergeRequest.merge_commit_sha==GitLabDeployment.sha, GitLabMergeRequest.project_id==GitLabDeployment.project_id)', foreign_keys='[GitLabDeployment.sha, GitLabDeployment.project_id]', viewonly=True)

    @hybrid_property
    def latest_deployment(self):
        """MR 关联的最新部署记录。"""
        if not self.deployments:
            return None
        return sorted(self.deployments, key=lambda d: d.created_at or d.updated_at, reverse=True)[0]

    @hybrid_property
    def risk_score(self):
        """变更风险评分 (0-100)。(黑科技 2/4 - AI 降噪)
        基于变更规模、评审轮次、质量门禁以及 AI 分类建议。
        """
        score = 0.0
        if self.raw_data:
            stats = self.raw_data.get('stats', {})
            additions = stats.get('additions', 0)
            deletions = stats.get('deletions', 0)
            score += (additions + deletions) / 100.0
        score += (self.review_cycles or 1) * 5
        if self.quality_gate_status == 'failed':
            score += 40
        if self.ai_category:
            cat = self.ai_category.lower()
            if 'bugfix' in cat or 'security' in cat:
                score *= 1.2
            elif 'documentation' in cat or 'test' in cat:
                score *= 0.2
            elif 'refactor' in cat:
                score *= 0.8
        return min(round(score, 1), 100.0)
    external_issue_id = Column(String(100))
    issue_source = Column(String(50))
    first_response_at = Column(DateTime(timezone=True))
    review_cycles = Column(Integer, default=1)
    human_comment_count = Column(Integer, default=0)
    approval_count = Column(Integer, default=0)
    review_time_total = Column(BigInteger)
    quality_gate_status = Column(String(20))
    ai_category = Column(String(50))
    ai_summary = Column(Text)
    ai_confidence = Column(Float)
    author_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    author = relationship('User', primaryjoin='and_(User.global_user_id==GitLabMergeRequest.author_id, User.is_current==True)')
    project = relationship('GitLabProject', back_populates='merge_requests')

    @hybrid_property
    def cycle_time(self):
        """MR 周期时长 (秒)。
        如果是已合并状态，计算从创建到合并的时间；否则返回 None。
        """
        if self.merged_at and self.created_at:
            start = self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=timezone.utc)
            end = self.merged_at if self.merged_at.tzinfo else self.merged_at.replace(tzinfo=timezone.utc)
            return (end - start).total_seconds()
        return None

    @cycle_time.expression
    def cycle_time(cls):
        """支持 SQL 过滤的周期时长表达式。"""
        return func.coalesce(cls.merged_at - cls.created_at, None)

    @hybrid_property
    def is_draft(self):
        """判断是否为草稿状态。"""
        if not self.raw_data:
            return False
        return self.raw_data.get('draft', False) or self.raw_data.get('work_in_progress', False)

    @hybrid_property
    def source_branch(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.raw_data.get('source_branch') if self.raw_data else None

    @hybrid_property
    def target_branch(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.raw_data.get('target_branch') if self.raw_data else None

    def __repr__(self) -> str:
        return f"<GitLabMergeRequest(id={self.id}, iid={self.iid})>"

class GitLabCommit(Base):
    """GitLab 提交模型。
    
    记录 Git 仓库的原子变更，并关联到项目和作者。
    
    Attributes:
        id (str): 完整的 Commit SHA。
        project_id (int): 所属项目 ID。
        short_id (str): 短 SHA。
        title (str): 标题（首行消息）。
        author_name (str): 作者姓名。
        author_email (str): 作者邮箱。
        message (str): 完整提交消息。
        authored_date (datetime): 作者日期。
        committed_date (datetime): 提交日期。
        additions (int): 新增行数。
        deletions (int): 删除行数。
        total (int): 总变动行数。
        is_off_hours (bool): 是否为非工作时间提交。
        linked_issue_ids (List[str]): 提取到的关联 Issues ID。
        issue_source (str): 关联 Issue 的来源 (jira, zentao, gitlab)。
        project (GitLabProject): 关联的项目。
        raw_data (dict): 原始 JSON 镜像存档。
    """
    __tablename__ = 'gitlab_commits'
    __table_args__ = {'extend_existing': True}
    id = Column(String, primary_key=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    short_id = Column(String)
    title = Column(String)
    author_name = Column(String)
    author_email = Column(String)
    message = Column(Text)
    authored_date = Column(DateTime(timezone=True))
    committed_date = Column(DateTime(timezone=True))
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    total = Column(Integer, default=0)
    is_off_hours = Column(Boolean, default=False)
    linked_issue_ids = Column(JSON)
    issue_source = Column(String(50))
    project = relationship('GitLabProject', back_populates='commits')
    raw_data = Column(JSON)
    gitlab_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True)
    author = relationship('User', primaryjoin='and_(User.global_user_id==GitLabCommit.gitlab_user_id, User.is_current==True)')

    def __repr__(self) -> str:
        return f"<GitLabCommit(id='{self.short_id}', project_id={self.project_id})>"

class GitLabCommitFileStats(Base):
    """提交文件级别统计模型。
    
    用于细粒度分析每次提交中不同类型文件的代码量和注释率。
    
    Attributes:
        id (int): 自增主键。
        commit_id (str): 关联的 Commit ID。
        file_path (str): 文件路径。
        language (str): 编程语言。
        file_type_category (str): 文件类型分类 (Code, Test, IaC, Config)。
        code_added (int): 新增代码行数。
        code_deleted (int): 删除代码行数。
        comment_added (int): 新增注释行数。
        comment_deleted (int): 删除注释行数。
        blank_added (int): 新增空行数。
        blank_deleted (int): 删除空行数。
        commit (Commit): 关联的 Commit 对象。
    """
    __tablename__ = 'gitlab_commit_file_stats'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    commit_id = Column(String, ForeignKey('gitlab_commits.id'))
    file_path = Column(String)
    language = Column(String)
    file_type_category = Column(String(50))
    code_added = Column(Integer, default=0)
    code_deleted = Column(Integer, default=0)
    comment_added = Column(Integer, default=0)
    comment_deleted = Column(Integer, default=0)
    blank_added = Column(Integer, default=0)
    blank_deleted = Column(Integer, default=0)
    commit = relationship('GitLabCommit')

    def __repr__(self) -> str:
        return f"<GitLabCommitFileStats(commit_id='{self.commit_id}', file_path='{self.file_path}')>"

class GitLabIssue(Base):
    """议题 (Issue) 模型。
    
    代表项目中的任务、缺陷或需求。
    
    Attributes:
        id (int): Issue 在 GitLab 中的唯一内部 ID。
        iid (int): 项目内 IID。
        project_id (int): 所属项目 ID。
        title (str): 任务标题。
        description (str): 任务详细描述。
        state (str): 状态 (opened, closed)。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
        closed_at (datetime): 关闭时间。
        time_estimate (int): 预估耗时 (秒)。
        total_time_spent (int): 实际累计耗时 (秒)。
        weight (int): 敏捷权重 (Story Points)。
        work_item_type (str): 工作项类型 (Issue, Task, Bug等)。
        ai_category (str): AI 自动分类建议。
        ai_summary (str): AI 生产的业务价值总结。
        ai_confidence (float): AI 置信度。
        labels (dict): 标签列表 (JSON)。
        author_id (UUID): 关联的系统内部作者 ID (mdm_identities.global_user_id)。
        author (User): 关联的 User 对象。
        project (Project): 关联的 Project 对象。
        events (List[GitLabIssueEvent]): 关联的状态变更事件流集合。
        transitions (List[IssueStateTransition]): 关联的状态流转历史集合。
        blockages (List[Blockage]): 关联的阻塞记录集合。
        raw_data (dict): 原始 JSON 镜像存档。
    """
    __tablename__ = 'gitlab_issues'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    iid = Column(Integer)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    title = Column(String)
    description = Column(String)
    state = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    time_estimate = Column(Integer)
    total_time_spent = Column(Integer)
    weight = Column(Integer)
    work_item_type = Column(String(50))
    ai_category = Column(String(50))
    ai_summary = Column(Text)
    ai_confidence = Column(Float)
    labels = Column(JSON)
    first_response_at = Column(DateTime(timezone=True))
    milestone_id = Column(Integer, ForeignKey('gitlab_milestones.id'), nullable=True)
    raw_data = Column(JSON)
    author_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    author = relationship('User', primaryjoin='and_(User.global_user_id==GitLabIssue.author_id, User.is_current==True)')
    project = relationship('GitLabProject', back_populates='issues')
    events = relationship('GitLabIssueEvent', back_populates='issue', cascade='all, delete-orphan')
    transitions = relationship('GitLabIssueStateTransition', back_populates='issue', cascade='all, delete-orphan')
    blockages = relationship('GitLabBlockage', back_populates='issue', cascade='all, delete-orphan')
    milestone = relationship('GitLabMilestone', back_populates='issues')
    merge_requests = relationship('GitLabMergeRequest', primaryjoin='and_(cast(GitLabIssue.iid, String)==GitLabMergeRequest.external_issue_id, GitLabIssue.project_id==GitLabMergeRequest.project_id)', viewonly=True, foreign_keys='[GitLabMergeRequest.external_issue_id, GitLabMergeRequest.project_id]')

    @hybrid_property
    def is_deployed(self):
        for mr in self.merge_requests:
            if any((d.is_success and d.is_production for d in mr.deployments)):
                return True
        return False

    @hybrid_property
    def deploy_environments(self):
        """该需求已部署到的所有环境列表。"""
        envs = set()
        for mr in self.merge_requests:
            for d in mr.deployments:
                if d.status == 'success':
                    envs.add(d.environment)
        return list(envs)
    associated_test_cases = relationship('GTMTestCase', secondary='gtm_test_case_issue_links', back_populates='linked_issues')

    @hybrid_property
    def resolution_time(self):
        """Issue 解决时长 (秒)。"""
        if self.closed_at and self.created_at:
            start = self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=timezone.utc)
            end = self.closed_at if self.closed_at.tzinfo else self.closed_at.replace(tzinfo=timezone.utc)
            return (end - start).total_seconds()
        return None

    @resolution_time.expression
    def resolution_time(cls):
        '''"""TODO: Add description.

Args:
    cls: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return func.coalesce(cls.closed_at - cls.created_at, None)

    @hybrid_property
    def age_in_current_state(self):
        """在当前状态已停留时长 (秒)。
        基于 updated_at 估算状态最后变更时间。
        """
        if self.updated_at:
            updated_at = self.updated_at if self.updated_at.tzinfo else self.updated_at.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - updated_at).total_seconds()
        return 0

    @hybrid_property
    def is_bug(self):
        """根据标签判定是否为 Bug。"""
        if not self.labels:
            return False
        return any(('bug' in str(label).lower() for label in self.labels))

    @hybrid_property
    def is_incident(self):
        """根据标签判定是否为 DORA 事故 (Incident)。"""
        if not self.labels:
            return False
        labels_str = str(self.labels).lower()
        return any((p.lower() in labels_str for p in settings.analysis.incident_label_patterns))

    @is_incident.expression
    def is_incident(cls):
        """DORA 事故检测的 SQL 表达式。"""
        from sqlalchemy import or_, Text
        conditions = [func.cast(cls.labels, Text).ilike(f'%{p}%') for p in settings.analysis.incident_label_patterns]
        return or_(*conditions)

    @hybrid_property
    def is_change_failure(self):
        """根据标签判定是否为变更失败 (Change Failure)。"""
        if not self.labels:
            return False
        labels_str = str(self.labels).lower()
        return any((p.lower() in labels_str for p in settings.analysis.change_failure_label_patterns))

    @is_change_failure.expression
    def is_change_failure(cls):
        """变更失败检测的 SQL 表达式。"""
        from sqlalchemy import or_, Text
        conditions = [func.cast(cls.labels, Text).ilike(f'%{p}%') for p in settings.analysis.change_failure_label_patterns]
        return or_(*conditions)

    @hybrid_property
    def priority_level(self):
        """从标签中解析优先级 (P0=0, P1=1, ...)。"""
        if not self.labels:
            return 99
        labels_str = str(self.labels).upper()
        if 'P0' in labels_str:
            return 0
        if 'P1' in labels_str:
            return 1
        if 'P2' in labels_str:
            return 2
        if 'P3' in labels_str:
            return 3
        if 'P4' in labels_str:
            return 4
        return 5

    @hybrid_property
    def sla_limit_seconds(self):
        """根据优先级确定的 SLA 响应阈值。"""
        thresholds = {0: settings.sla.p0 * 3600, 1: settings.sla.p1 * 3600, 2: settings.sla.p2 * 3600, 3: settings.sla.p3 * 3600, 4: settings.sla.p4 * 3600}
        return thresholds.get(self.priority_level, settings.sla.default * 3600)

    @hybrid_property
    def is_sla_violated(self):
        """是否违反了 SLA 响应承诺。"""
        if not self.created_at:
            return False
        start = self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=timezone.utc)
        raw_end = self.first_response_at or datetime.now(timezone.utc)
        end = raw_end if raw_end.tzinfo else raw_end.replace(tzinfo=timezone.utc)
        response_time = (end - start).total_seconds()
        return response_time > self.sla_limit_seconds

    @hybrid_property
    def sla_status(self):
        """SLA 状态语义化输出。"""
        if self.first_response_at:
            return 'SUCCESS' if not self.is_sla_violated else 'VIOLATED'
        return 'WARNING' if self.is_sla_violated else 'PENDING'

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabIssue(id={self.id}, iid={self.iid}, title='{self.title}')>"

class GitLabIssueEvent(Base):
    """GitLab Issue 变更事件流。
    
    CALMS 扫描核心表，用于根据事件流重建 Issue 的状态演进过程（如前置时间计算）。
    
    Attributes:
        id (int): 自增主键。
        issue_id (int): 关联的 Issue ID。
        user_id (UUID): 触发该事件的用户 ID (mdm_identities.global_user_id)。
        event_type (str): 事件类型 (state, label, milestone, iteration)。
        action (str): 动作类型 (add, remove, closed, reopened, update)。
        external_event_id (int): GitLab 侧的原始 Event ID。
        meta_info (dict): 存储具体的变更内容（如标签名、状态值等）。
        created_at (datetime): 事件发生时间。
        issue (Issue): 关联的 Issue 对象。
        user (User): 关联的 User 对象。
    """
    __tablename__ = 'gitlab_issue_events'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey('gitlab_issues.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    event_type = Column(String(50))
    action = Column(String(50))
    external_event_id = Column(Integer)
    meta_info = Column(JSON)
    created_at = Column(DateTime(timezone=True))
    issue = relationship('GitLabIssue', back_populates='events')
    user = relationship('User')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabIssueEvent(issue_id={self.issue_id}, type='{self.event_type}')>"

class GitLabIssueStateTransition(Base):
    """Issue 状态流转记录。
    
    用于计算 Cycle Time 和分析流动效率。
    
    Attributes:
        id (int): 自增主键。
        issue_id (int): 关联的 Issue ID。
        from_state (str): 变更前状态。
        to_state (str): 变更后状态。
        timestamp (datetime): 状态变更时间。
        duration_hours (float): 在上一状态停留的时长 (小时)。
        issue (Issue): 关联的 Issue 对象。
    """
    __tablename__ = 'gitlab_issue_state_transitions'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey('gitlab_issues.id'), nullable=False)
    from_state = Column(String(50))
    to_state = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    duration_hours = Column(Float)
    issue = relationship('GitLabIssue', back_populates='transitions')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabIssueStateTransition(issue_id={self.issue_id}, to_state='{self.to_state}')>"

class GitLabBlockage(Base):
    """Issue 阻塞记录。
    
    用于分析阻碍流动的原因和时长 (Flow Efficiency)。
    
    Attributes:
        id (int): 自增主键。
        issue_id (int): 关联的 Issue ID。
        reason (str): 阻塞原因。
        start_time (datetime): 阻塞开始时间。
        end_time (datetime): 阻塞结束时间。
        issue (Issue): 关联的 Issue 对象。
    """
    __tablename__ = 'gitlab_issue_blockages'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey('gitlab_issues.id'), nullable=False)
    reason = Column(String(200))
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    issue = relationship('GitLabIssue', back_populates='blockages')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabBlockage(issue_id={self.issue_id}, reason='{self.reason}')>"

class GitLabPipeline(Base):
    """流水线 (CI/CD Pipeline) 模型。
    
    记录 CI/CD 执行的结果、时长和覆盖率等工程效能核心指标。
    
    Attributes:
        id (int): 流水线在 GitLab 中的唯一 ID。
        project_id (int): 所属项目 ID。
        status (str): 状态 (success, failed, canceled, skipped)。
        ref (str): 分支或标签。
        sha (str): 触发流水线的 Commit SHA。
        source (str): 触发源 (push, web, schedule 等)。
        duration (int): 执行总时长 (秒)。
        created_at (datetime): 创建时间。
        updated_at (datetime): 最后更新时间。
        coverage (str): 测试覆盖率。
        failure_reason (str): 失败原因。
        raw_data (dict): 原始 JSON。
        project (Project): 关联的 Project 对象。
    """
    __tablename__ = 'gitlab_pipelines'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
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
    project = relationship('GitLabProject', back_populates='pipelines')

    @hybrid_property
    def is_success(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.status == 'success'

    @is_success.expression
    def is_success(cls):
        '''"""TODO: Add description.

Args:
    cls: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return cls.status == 'success'

    @hybrid_property
    def is_failed(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.status == 'failed'

    @is_failed.expression
    def is_failed(cls):
        '''"""TODO: Add description.

Args:
    cls: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return cls.status == 'failed'

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabPipeline(id={self.id}, project_id={self.project_id}, status='{self.status}')>"

class GitLabDeployment(Base):
    """部署记录模型。
    
    记录代码被部署到不同环境的执行结果及其追踪 SHA。
    
    Attributes:
        id (int): 部署在 GitLab 中的唯一内部 ID。
        iid (int): 项目内 IID。
        project_id (int): 所属项目 ID。
        status (str): 部署状态 (created, running, success, failed, canceled)。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
        ref (str): 部署的分支或标签。
        sha (str): 部署的 Commit SHA。
        environment (str): 部署环境名称 (如 production, staging)。
        raw_data (dict): 原始 JSON。
        project (Project): 关联的 Project 对象。
    """
    __tablename__ = 'gitlab_deployments'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    iid = Column(Integer)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    status = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    ref = Column(String)
    sha = Column(String)
    environment = Column(String)
    raw_data = Column(JSON)
    project = relationship('GitLabProject', back_populates='deployments')

    @hybrid_property
    def is_success(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return self.status == 'success'

    @is_success.expression
    def is_success(cls):
        '''"""TODO: Add description.

Args:
    cls: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return cls.status == 'success'

    @hybrid_property
    def is_production(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        if not self.environment:
            return False
        return self.environment.lower() in ['production', 'prod']

    @is_production.expression
    def is_production(cls):
        '''"""TODO: Add description.

Args:
    cls: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return func.lower(cls.environment).in_(['production', 'prod'])

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabDeployment(id={self.id}, env='{self.environment}', status='{self.status}')>"

class GitLabNote(Base):
    """评论/笔记模型。
    
    存储 Issue、MR 等对象下的讨论内容和系统通知。
    
    Attributes:
        id (int): Note 在 GitLab 中的唯一 ID。
        project_id (int): 所属项目 ID。
        noteable_type (str): 被评论的对象类型 (MergeRequest, Issue, Commit)。
        noteable_iid (int): 被评论对象的 IID。
        body (str): 评论的正文内容。
        author_id (UUID): 评论者在系统中的全局 ID。
        created_at (datetime): 评论创建时间。
        updated_at (datetime): 评论更新时间。
        system (bool): 是否为系统产生的评论及通知。
        resolvable (bool): 是否为可解决的评价。
        raw_data (dict): 原始 JSON。
        project (Project): 关联的项目对象。
    """
    __tablename__ = 'gitlab_notes'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    noteable_type = Column(String)
    noteable_iid = Column(Integer)
    body = Column(String)
    author_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    system = Column(Boolean)
    resolvable = Column(Boolean)
    raw_data = Column(JSON)
    project = relationship('GitLabProject')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabNote(id={self.id}, type='{self.noteable_type}')>"

class GitLabTag(Base):
    """标签/版本号模型。
    
    Attributes:
        id (int): 数据库自增 ID。
        project_id (int): 所属项目 ID。
        name (str): 标签名称。
        message (str): 标签消息。
        commit_sha (str): 对应的 Commit SHA。
        created_at (datetime): 创建时间。
        project (Project): 关联的 Project 对象。
    """
    __tablename__ = 'gitlab_tags'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    name = Column(String)
    message = Column(String)
    commit_sha = Column(String)
    created_at = Column(DateTime(timezone=True))
    project = relationship('GitLabProject')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabTag(name='{self.name}', project_id={self.project_id})>"

class GitLabBranch(Base):
    """分支模型。
    
    Attributes:
        id (int): 数据库自增 ID。
        project_id (int): 所属项目 ID。
        name (str): 分支名称。
        last_commit_sha (str): 最后一次提交的 SHA。
        last_commit_date (datetime): 最后一次提交的时间。
        last_committer_name (str): 最后一次提交的作者。
        is_merged (bool): 是否已合并。
        is_protected (bool): 是否为保护分支。
        is_default (bool): 是否为默认分支。
        raw_data (dict): 原始 JSON。
        project (Project): 关联的项目对象。
    """
    __tablename__ = 'gitlab_branches'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    name = Column(String)
    last_commit_sha = Column(String)
    last_commit_date = Column(DateTime(timezone=True))
    last_committer_name = Column(String)
    is_merged = Column(Boolean)
    is_protected = Column(Boolean)
    is_default = Column(Boolean)
    raw_data = Column(JSON)
    project = relationship('GitLabProject')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabBranch(name='{self.name}', project_id={self.project_id})>"

class GitLabMilestone(Base):
    """里程碑模型。
    
    Attributes:
        id (int): GitLab Milestone 的全局唯一 ID。
        iid (int): 项目内 IID。
        project_id (int): 所属项目 ID。
        title (str): 里程碑标题。
        description (str): 描述内容。
        state (str): 状态 (active, closed)。
        due_date (datetime): 截止日期。
        start_date (datetime): 开始日期。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
        raw_data (dict): 原始 JSON。
        project (Project): 关联的 Project 对象。
        releases (List[GitLabRelease]): 关联的发布记录列表。
    """
    __tablename__ = 'gitlab_milestones'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    iid = Column(Integer)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    title = Column(String)
    description = Column(String)
    state = Column(String)
    due_date = Column(DateTime(timezone=True))
    start_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    raw_data = Column(JSON)
    project = relationship('GitLabProject', back_populates='milestones')
    releases = relationship('GitLabRelease', secondary='release_milestone_links', back_populates='milestones')
    issues = relationship('GitLabIssue', back_populates='milestone')

    @hybrid_property
    def progress(self):
        """里程碑完成进度 (百分比)。"""
        total = len(self.issues)
        if total == 0:
            return 0.0
        closed = len([i for i in self.issues if i.state == 'closed'])
        return closed / total * 100

    @hybrid_property
    def is_overdue(self):
        """是否已逾期。"""
        if self.state == 'closed':
            return False
        if self.due_date:
            return datetime.now(timezone.utc) > self.due_date
        return False

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabMilestone(id={self.id}, title='{self.title}')>"

class ReleaseMilestoneLink(Base):
    """发布与里程碑的关联表。
    
    实现 Release 与 Milestone 的多对多关联。

    Attributes:
        release_id (int): 关联的 Release ID。
        milestone_id (int): 关联的 Milestone ID。
    """
    __tablename__ = 'release_milestone_links'
    __table_args__ = {'extend_existing': True}
    release_id = Column(Integer, ForeignKey('gitlab_releases.id'), primary_key=True)
    milestone_id = Column(Integer, ForeignKey('gitlab_milestones.id'), primary_key=True)

class GitLabRelease(Base):
    """GitLab 发布记录模型。
    
    对应 GitLab 的 Release 对象。一个 Release 基于一个 Tag，可以关联多个 Milestone。

    Attributes:
        id (int): 本地自增 ID。
        project_id (int): 所属项目 ID。
        tag_name (str): Release 的唯一标识 (Tag Name)。
        name (str): Release 标题。
        description (str): Release Notes。
        created_at (datetime): 创建时间。
        released_at (datetime): 发布时间。
        author_id (UUID): 关联的系统内部用户 ID (mdm_identities.global_user_id)。
        raw_data (dict): 原始数据。
        project (Project): 关联的 Project 对象。
        milestones (List[Milestone]): 关联的 Milestone 列表。
    """
    __tablename__ = 'gitlab_releases'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'), nullable=False)
    tag_name = Column(String(255), nullable=False)
    name = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True))
    released_at = Column(DateTime(timezone=True))
    author_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    raw_data = Column(JSON)
    project = relationship('GitLabProject')
    milestones = relationship('GitLabMilestone', secondary='release_milestone_links', back_populates='releases')

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabRelease(id={self.id}, tag='{self.tag_name}')>"

class GitLabPackage(Base):
    """GitLab 制品库包模型。
    
    Attributes:
        id (int): GitLab Package ID。
        project_id (int): 所属项目 ID。
        name (str): 包名。
        version (str): 版本号。
        package_type (str): 包类型 (maven, npm, pypi等)。
        status (str): 状态。
        created_at (datetime): 创建时间。
        web_url (str): Web 链接。
        project (Project): 关联的 Project 对象。
        files (List[GitLabPackageFile]): 该包包含的文件。
        raw_data (dict): 原始 JSON。
    """
    __tablename__ = 'gitlab_packages'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    name = Column(String(255), nullable=False)
    version = Column(String(100))
    package_type = Column(String(50))
    status = Column(String(50))
    created_at = Column(DateTime(timezone=True))
    web_url = Column(String(500))
    project = relationship('GitLabProject')
    files = relationship('GitLabPackageFile', back_populates='package', cascade='all, delete-orphan')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabPackage(id={self.id}, name='{self.name}', version='{self.version}')>"

class GitLabPackageFile(Base):
    """GitLab 包关联的文件模型。
    
    Attributes:
        id (int): GitLab Package File ID。
        package_id (int): 关联的包 ID。
        file_name (str): 文件名。
        size (int): 文件大小 (bytes)。
        file_sha1 (str): SHA1 校验值。
        file_sha256 (str): SHA256 校验值。
        created_at (datetime): 创建时间。
        package (GitLabPackage): 关联的 GitLabPackage 对象。
        raw_data (dict): 原始 JSON。
    """
    __tablename__ = 'gitlab_package_files'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    package_id = Column(Integer, ForeignKey('gitlab_packages.id'))
    file_name = Column(String(255), nullable=False)
    size = Column(BigInteger)
    file_sha1 = Column(String(40))
    file_sha256 = Column(String(64))
    created_at = Column(DateTime(timezone=True))
    package = relationship('GitLabPackage', back_populates='files')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabPackageFile(id={self.id}, name='{self.file_name}')>"

class GitLabWikiLog(Base):
    """GitLab Wiki 变更日志模型。
    
    Attributes:
        id (int): 自增主键。
        project_id (int): 所属项目 ID。
        title (str): Wiki 页面标题。
        slug (str): Wiki 页面路径。
        format (str): 文档格式。
        action (str): 变更动作 (created, updated, deleted)。
        user_id (UUID): 操作者 ID (mdm_identities.global_user_id)。
        created_at (datetime): 操作时间。
        project (Project): 关联的项目对象。
        user (User): 关联的用户对象。
        raw_data (dict): 原始 JSON。
    """
    __tablename__ = 'gitlab_wiki_logs'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    title = Column(String(255))
    slug = Column(String(255))
    format = Column(String(20))
    action = Column(String(50))
    user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    created_at = Column(DateTime(timezone=True))
    project = relationship('GitLabProject')
    user = relationship('User')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabWikiLog(id={self.id}, action='{self.action}', title='{self.title}')>"

class GitLabDependency(Base):
    """GitLab 项目依赖模型。
    
    Attributes:
        id (int): 自增主键。
        project_id (int): 所属项目 ID。
        name (str): 依赖包名。
        version (str): 依赖版本。
        package_manager (str): 包管理器 (maven, npm 等)。
        dependency_type (str): 依赖类型 (direct, transitive)。
        project (Project): 关联的项目对象。
        raw_data (dict): 原始 JSON。
    """
    __tablename__ = 'gitlab_dependencies'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('gitlab_projects.id'))
    name = Column(String(255), nullable=False)
    version = Column(String(100))
    package_manager = Column(String(50))
    dependency_type = Column(String(50))
    project = relationship('GitLabProject')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<GitLabDependency(id={self.id}, name='{self.name}', version='{self.version}')>"
from . import events
events.register_events()
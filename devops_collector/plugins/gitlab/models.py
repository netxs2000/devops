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
    """GitLab 群组模型。"""
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
    """GitLab 群组成员模型。"""
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
    """GitLab 项目模型。"""
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
    """合并请求 (MR) 模型。"""
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
    
    author_id = Column(Integer, ForeignKey('users.id'))
    author = relationship("User")
    
    project = relationship("Project")


class Commit(Base):
    """代码提交记录模型。"""
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
    
    gitlab_user_id = Column(Integer, ForeignKey('users.id'))
    author_user = relationship("User")
    
    project = relationship("Project")


class CommitFileStats(Base):
    """提交文件级别统计模型。"""
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
    """议题 (Issue) 模型。"""
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


class Pipeline(Base):
    """流水线 (CI/CD Pipeline) 模型。"""
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
    """部署记录模型。"""
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
    """评论/笔记模型。"""
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
    """标签/版本号模型。"""
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    name = Column(String)
    message = Column(String)
    commit_sha = Column(String) 
    created_at = Column(DateTime(timezone=True)) 
    
    project = relationship("Project")


class Branch(Base):
    """分支模型。"""
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
    """里程碑模型。"""
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
    """GitLab 制品库包模型。"""
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
    """GitLab 包关联的文件模型。"""
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

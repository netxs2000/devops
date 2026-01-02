"""GitLab Issue 镜像元数据模型模块。

本模块定义了用于高性能过滤和部门隔离的 Issue 本地缓存索引表。
该表同步自 GitLab API，并根据项目和作者的扩展信息注入部门属性。

Typical Usage:
    from devops_collector.gitlab_sync.models.issue_metadata import IssueMetadata
    issue = db.query(IssueMetadata).filter_by(gitlab_issue_iid=101).first()
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from devops_collector.models.base_models import Base

class IssueMetadata(Base):
    """GitLab Issue 本地镜像索引表 (实现部门隔离)。

    该表存放 Issue 的核心元数据索引，旨在实现跨项目、跨部门的高性能看板展示。

    Attributes:
        id (int): 自增主键。
        gitlab_project_id (int): GitLab 项目 ID。
        gitlab_issue_iid (int): GitLab Issue 内部 IID。
        global_issue_id (int): GitLab 全局唯一 ID。
        dept_name (str): 归属部门名（同步自顶级群组描述）。
        title (str): Issue 标题。
        state (str): 状态 (opened/closed)。
        author_username (str): 提报人用户名。
        author_dept_name (str): 提报人部门名（同步自 Skype 字段）。
        assignee_username (str): 负责人用户名。
        issue_type (str): 类型 (bug/requirement/task)。
        priority (str): 优先级 (P0/P1/P2)。
        gitlab_created_at (datetime): 原始创建时间。
        gitlab_updated_at (datetime): 原始更新时间。
        last_synced_at (datetime): 入库同步时间。
        sync_status (int): 状态位 (1: 有效, 0: 已软删除)。
    """
    __tablename__ = 'issue_metadata'
    id = Column(Integer, primary_key=True, autoincrement=True)
    gitlab_project_id = Column(Integer, nullable=False, index=True)
    gitlab_issue_iid = Column(Integer, nullable=False)
    global_issue_id = Column(Integer, nullable=False)
    dept_name = Column(String(100), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    state = Column(String(20), nullable=False)
    author_username = Column(String(64))
    author_dept_name = Column(String(100), index=True)
    assignee_username = Column(String(64))
    issue_type = Column(String(20), default='bug')
    priority = Column(String(20))
    gitlab_created_at = Column(DateTime(timezone=True))
    gitlab_updated_at = Column(DateTime(timezone=True))
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sync_status = Column(Integer, default=1)
    __table_args__ = (UniqueConstraint('gitlab_project_id', 'gitlab_issue_iid', name='idx_project_issue_unique'), Index('idx_dept_state_type', 'dept_name', 'state', 'issue_type'), Index('idx_author_search', 'author_username'))
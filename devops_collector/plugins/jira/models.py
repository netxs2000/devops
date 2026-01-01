"""Jira 数据模型

定义 Jira 相关的 SQLAlchemy ORM 模型，包括项目、看板、Sprint 和 Issue。
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

# 从公共基础模型导入 Base
from devops_collector.models.base_models import Base

class JiraProject(Base):
    """Jira 项目模型 (jira_projects)。
    
    Attributes:
        id (int): 自增内部主键。
        key (str): Jira 项目的唯一标识符 (e.g. 'PROJ')。
        name (str): 项目名称。
        description (str): 项目描述。
        lead_name (str): 项目负责人。
        gitlab_project_id (int): 关联的 GitLab 项目 ID。
        last_synced_at (datetime): 最近同步时间。
        sync_status (str): 同步状态 (PENDING, SUCCESS, FAILED)。
        boards (List[JiraBoard]): 关联的看板列表。
        issues (List[JiraIssue]): 关联的问题列表。
    """
    __tablename__ = 'jira_projects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    lead_name = Column(String(255))
    
    gitlab_project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    gitlab_project = relationship("Project", back_populates="jira_projects")
    
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='PENDING')
    
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)
    )
    
    raw_data = Column(JSON)
    
    boards = relationship(
        "JiraBoard", back_populates="project", cascade="all, delete-orphan"
    )
    issues = relationship(
        "JiraIssue", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<JiraProject(key='{self.key}', name='{self.name}')>"


class JiraBoard(Base):
    """Jira 看板模型 (jira_boards)。

    Attributes:
        id (int): Jira 原始 Board ID。
        project_id (int): 关联的 Jira 项目 ID。
        name (str): 看板名称。
        type (str): 看板类型 (kanban, scrum)。
        project (JiraProject): 关联的项目。
        sprints (List[JiraSprint]): 关联的迭代列表。
    """
    __tablename__ = 'jira_boards'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('jira_projects.id'), nullable=False)
    name = Column(String(255))
    type = Column(String(50))
    
    project = relationship("JiraProject", back_populates="boards")
    sprints = relationship(
        "JiraSprint", back_populates="board", cascade="all, delete-orphan"
    )
    
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<JiraBoard(id={self.id}, name='{self.name}')>"


class JiraSprint(Base):
    """Jira Sprint (迭代) 模型 (jira_sprints)。

    Attributes:
        id (int): Jira 原始 Sprint ID。
        board_id (int): 关联的看板 ID。
        name (str): Sprint 名称。
        state (str): 状态 (active, closed, future)。
        start_date (datetime): 开始日期。
        end_date (datetime): 计划结束日期。
        complete_date (datetime): 实际完成日期。
        board (JiraBoard): 关联的看板。
        issues (List[JiraIssue]): 关联的问题列表。
    """
    __tablename__ = 'jira_sprints'
    
    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey('jira_boards.id'), nullable=False)
    name = Column(String(255))
    state = Column(String(20))
    
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    complete_date = Column(DateTime(timezone=True))
    
    board = relationship("JiraBoard", back_populates="sprints")
    issues = relationship("JiraIssue", back_populates="sprint")
    
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<JiraSprint(id={self.id}, name='{self.name}', state='{self.state}')>"


class JiraIssue(Base):
    """Jira Issue (问题/任务) 详情模型 (jira_issues)。

    Attributes:
        id (int): Jira 原始 Issue ID。
        key (str): 问题 Key (e.g. 'PROJ-123')。
        project_id (int): 所属项目 ID。
        sprint_id (int): 当前所属 Sprint ID。
        summary (str): 概要标题。
        description (str): 详细描述。
        status (str): 当前状态。
        priority (str): 优先级。
        issue_type (str): 类型 (Story, Bug, Task 等)。
        assignee_user_id (UUID): 负责人的 OneID。
        reporter_user_id (UUID): 报告人的 OneID。
        creator_user_id (UUID): 创建人的 OneID。
        reopening_count (int): 重开次数。
        time_to_first_response (int): 响应延迟 (秒)。
        original_estimate (int): 原始预估工时 (秒)。
        time_spent (int): 实际消耗工时 (秒)。
        labels (list): 标签列表 (JSON)。
        fix_versions (list): 修复版本列表 (JSON)。
    """
    __tablename__ = 'jira_issues'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    project_id = Column(Integer, ForeignKey('jira_projects.id'), nullable=False)
    sprint_id = Column(Integer, ForeignKey('jira_sprints.id'), nullable=True)
    
    summary = Column(String(500))
    description = Column(Text)
    status = Column(String(50))
    priority = Column(String(50))
    issue_type = Column(String(50))
    
    assignee_name = Column(String(255))
    reporter_name = Column(String(255))
    creator_name = Column(String(255))
    
    assignee_user_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True
    )
    reporter_user_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True
    )
    creator_user_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True
    )
    
    user_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True
    )
    
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    
    raw_data = Column(JSON)
    
    first_commit_sha = Column(String(100))
    first_fix_date = Column(DateTime(timezone=True))
    
    reopening_count = Column(Integer, default=0)
    time_to_first_response = Column(BigInteger)
    
    original_estimate = Column(BigInteger)
    time_spent = Column(BigInteger)
    remaining_estimate = Column(BigInteger)
    
    labels = Column(JSON)
    fix_versions = Column(JSON)
    
    project = relationship("JiraProject", back_populates="issues")
    history = relationship(
        "JiraIssueHistory", back_populates="issue", cascade="all, delete-orphan"
    )
    sprint = relationship("JiraSprint", back_populates="issues")

    def __repr__(self) -> str:
        return f"<JiraIssue(key='{self.key}', summary='{self.summary[:20]}...')>"


class JiraIssueHistory(Base):
    """Jira 问题变更历史表 (jira_issue_histories)。

    Attributes:
        id (str): Jira History ID。
        issue_id (int): 关联的问题 ID。
        author_name (str): 变更人名称。
        field (str): 变更字段。
        from_string (str): 变更前的值。
        to_string (str): 变更后的值。
    """
    __tablename__ = 'jira_issue_histories'
    
    id = Column(String(50), primary_key=True)
    issue_id = Column(Integer, ForeignKey('jira_issues.id'), nullable=False)
    
    author_name = Column(String(100))
    created_at = Column(DateTime(timezone=True))
    
    field = Column(String(100))
    from_string = Column(Text)
    to_string = Column(Text)
    
    issue = relationship("JiraIssue", back_populates="history")
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<JiraIssueHistory(issue_id={self.issue_id}, field='{self.field}')>"

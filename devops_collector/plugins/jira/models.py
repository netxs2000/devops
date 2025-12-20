"""Jira 数据模型

定义 Jira 相关的 SQLAlchemy ORM 模型，包括项目、看板、Sprint 和 Issue。
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, BigInteger
from sqlalchemy.orm import relationship

# 从公共基础模型导入 Base
from devops_collector.models.base_models import Base

class JiraProject(Base):
    """Jira 项目模型。
    
    Attributes:
        key: Jira 项目的唯一标识符 (如 'PROJ')
        name: 项目名称
    """
    __tablename__ = 'jira_projects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    lead_name = Column(String(255))
    
    # 关联 GitLab 项目 (可选)
    gitlab_project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    
    # 同步状态
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='PENDING')
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    raw_data = Column(JSON)
    
    # 关联
    boards = relationship("JiraBoard", back_populates="project", cascade="all, delete-orphan")
    issues = relationship("JiraIssue", back_populates="project", cascade="all, delete-orphan")


class JiraBoard(Base):
    """Jira 看板模型。"""
    __tablename__ = 'jira_boards'
    
    id = Column(Integer, primary_key=True)  # Jira 原始 Board ID
    project_id = Column(Integer, ForeignKey('jira_projects.id'), nullable=False)
    name = Column(String(255))
    type = Column(String(50))  # kanban, scrum
    
    project = relationship("JiraProject", back_populates="boards")
    sprints = relationship("JiraSprint", back_populates="board", cascade="all, delete-orphan")
    
    raw_data = Column(JSON)


class JiraSprint(Base):
    """Jira Sprint (迭代) 模型。"""
    __tablename__ = 'jira_sprints'
    
    id = Column(Integer, primary_key=True)  # Jira 原始 Sprint ID
    board_id = Column(Integer, ForeignKey('jira_boards.id'), nullable=False)
    name = Column(String(255))
    state = Column(String(20))  # active, closed, future
    
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    complete_date = Column(DateTime(timezone=True))
    
    board = relationship("JiraBoard", back_populates="sprints")
    issues = relationship("JiraIssue", back_populates="sprint")
    
    raw_data = Column(JSON)


class JiraIssue(Base):
    """Jira Issue (问题/任务) 详情模型。"""
    __tablename__ = 'jira_issues'
    
    id = Column(Integer, primary_key=True)  # Jira 原始 Issue ID
    key = Column(String(50), unique=True, nullable=False)
    project_id = Column(Integer, ForeignKey('jira_projects.id'), nullable=False)
    sprint_id = Column(Integer, ForeignKey('jira_sprints.id'), nullable=True)
    
    summary = Column(String(500))
    description = Column(Text)
    status = Column(String(50))
    priority = Column(String(50))
    issue_type = Column(String(50))  # Story, Bug, Task, etc.
    
    assignee_name = Column(String(255))
    reporter_name = Column(String(255))
    creator_name = Column(String(255))
    
    # 关联系统全局用户
    assignee_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    reporter_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    creator_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # 向后兼容
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    
    # 原始数据
    raw_data = Column(JSON)
    
    # 链路追溯：代码修复记录
    first_commit_sha = Column(String(100))
    first_fix_date = Column(DateTime(timezone=True))
    
    # 行为特征：协作体验 (Developer Experience)
    reopening_count = Column(Integer, default=0)        # 重开次数 (从 Done/Resolved 回到 In Progress)
    time_to_first_response = Column(BigInteger)         # 响应延迟 (创建到首次分配或状态变更的时间，秒)
    
    # PMO 指标扩展：进度与预估
    original_estimate = Column(BigInteger)              # 原始预估工时 (秒)
    time_spent = Column(BigInteger)                     # 实际消耗工时 (秒)
    remaining_estimate = Column(BigInteger)              # 剩余预估工时 (秒)
    
    # 标签与版本 (用于里程碑、风险、战略分类)
    labels = Column(JSON)                               # 标签列表 (数组)
    fix_versions = Column(JSON)                         # 修复版本 (数组，包含标识里程碑的信息)
    
    project = relationship("JiraProject", back_populates="issues")
    history = relationship("JiraIssueHistory", back_populates="issue", cascade="all, delete-orphan")
    sprint = relationship("JiraSprint", back_populates="issues")


class JiraIssueHistory(Base):
    """Jira 问题变更历史。"""
    __tablename__ = 'jira_issue_histories'
    
    id = Column(String(50), primary_key=True)  # Jira History ID
    issue_id = Column(Integer, ForeignKey('jira_issues.id'), nullable=False)
    
    author_name = Column(String(100))
    created_at = Column(DateTime(timezone=True))
    
    field = Column(String(100))
    from_string = Column(Text)
    to_string = Column(Text)
    
    issue = relationship("JiraIssue", back_populates="history")
    raw_data = Column(JSON)

"""Jenkins 数据模型

定义 Jenkins 相关的 SQLAlchemy ORM 模型，包括 Job 和 Build 详情。
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, BigInteger
from sqlalchemy.orm import relationship

# 从公共基础模型导入 Base
from devops_collector.models.base_models import Base


class JenkinsJob(Base):
    """Jenkins 任务(Job)模型。
    
    存储 Jenkins Job 的基本信息。
    
    Attributes:
        full_name: Job 的完整名称 (包含路径，如 folder/my-job)
        url: Job 的访问链接
    """
    __tablename__ = 'jenkins_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    full_name = Column(String(500), unique=True, nullable=False)
    url = Column(String(500))
    description = Column(Text)
    color = Column(String(50))  # 状态颜色 (blue, red, anime等)
    
    # 关联 GitLab 项目 (可选，通过名称匹配)
    gitlab_project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    
    # 同步状态
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='PENDING')
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    # 原始数据
    raw_data = Column(JSON)
    
    # 关联
    builds = relationship("JenkinsBuild", back_populates="job", cascade="all, delete-orphan")


class JenkinsBuild(Base):
    """Jenkins 构建(Build)详情模型。
    
    记录每次构建的具体信息。
    
    Attributes:
        number: 构建编号
        result: 构建结果 (SUCCESS, FAILURE, ABORTED, UNSTABLE)
        duration: 耗时 (毫秒)
        timestamp: 构建开始时间
    """
    __tablename__ = 'jenkins_builds'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey('jenkins_jobs.id'), nullable=False)
    number = Column(Integer, nullable=False)
    
    queue_id = Column(BigInteger)
    url = Column(String(500))
    
    result = Column(String(20))  # SUCCESS, FAILURE, ABORTED, UNSTABLE
    duration = Column(BigInteger)  # 耗时 (ms)
    timestamp = Column(DateTime(timezone=True))  # 构建开始时间
    
    building = Column(Boolean, default=False)
    executor = Column(String(255))
    
    # 构建原因/触发者 (可能是用户、GitLab Webhook 等)
    trigger_type = Column(String(50))
    trigger_user = Column(String(100))
    trigger_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # 关联 GitLab 提交 (如果能获取到)
    commit_sha = Column(String(100))
    
    # 原始数据
    raw_data = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    job = relationship("JenkinsJob", back_populates="builds")

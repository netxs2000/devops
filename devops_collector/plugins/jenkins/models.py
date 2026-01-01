"""Jenkins 数据模型

定义 Jenkins 相关的 SQLAlchemy ORM 模型，包括 Job 和 Build 详情。
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

# 从公共基础模型导入 Base
from devops_collector.models.base_models import Base


class JenkinsJob(Base):
    """Jenkins 任务(Job)模型 (jenkins_jobs)。
    
    存储 Jenkins Job 的基本信息。
    
    Attributes:
        id (int): 自增主键。
        name (str): Job 名称。
        full_name (str): Job 的完整名称 (包含路径，如 folder/my-job)。
        url (str): Job 的访问链接。
        color (str): 状态颜色 (blue, red, anime 等)。
        gitlab_project_id (int): 关联的 GitLab 项目 ID。
        last_synced_at (datetime): 最近同步时间。
        sync_status (str): 同步状态 (PENDING, SUCCESS, FAILED)。
        builds (List[JenkinsBuild]): 关联的构建列表。
    """
    __tablename__ = 'jenkins_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    full_name = Column(String(500), unique=True, nullable=False)
    url = Column(String(500))
    description = Column(Text)
    color = Column(String(50))
    
    gitlab_project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String(20), default='PENDING')
    
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc)
    )
    
    raw_data = Column(JSON)
    
    builds = relationship(
        "JenkinsBuild", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<JenkinsJob(full_name='{self.full_name}')>"


class JenkinsBuild(Base):
    """Jenkins 构建(Build)详情模型 (jenkins_builds)。
    
    记录每次构建的具体信息。
    
    Attributes:
        id (int): 自增主键。
        job_id (int): 所属 Job ID。
        number (int): 构建编号。
        result (str): 构建结果 (SUCCESS, FAILURE, ABORTED, UNSTABLE)。
        duration (int): 耗时 (毫秒)。
        timestamp (datetime): 构建开始时间。
        building (bool): 是否正在构建中。
        executor (str): 执行节点名称。
        trigger_type (str): 触发类型。
        trigger_user (str): 触发人。
        trigger_user_id (UUID): 触发人 OneID。
        commit_sha (str): 关联的代码提交哈希。
        gitlab_mr_iid (int): 关联的 GitLab MR IID。
        artifact_id (str): 产物版本或地址。
        artifact_type (str): 产物类型 (docker_image, jar 等)。
        job (JenkinsJob): 关联的 Job 对象。
    """
    __tablename__ = 'jenkins_builds'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey('jenkins_jobs.id'), nullable=False)
    number = Column(Integer, nullable=False)
    
    queue_id = Column(BigInteger)
    url = Column(String(500))
    
    result = Column(String(20))
    duration = Column(BigInteger)
    timestamp = Column(DateTime(timezone=True))
    
    building = Column(Boolean, default=False)
    executor = Column(String(255))
    
    trigger_type = Column(String(50))
    trigger_user = Column(String(100))
    trigger_user_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'), nullable=True
    )
    
    commit_sha = Column(String(100))
    
    raw_data = Column(JSON)
    
    gitlab_mr_iid = Column(Integer)
    artifact_id = Column(String(200))
    artifact_type = Column(String(50))
    
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    
    job = relationship("JenkinsJob", back_populates="builds")

    def __repr__(self) -> str:
        return f"<JenkinsBuild(job_id={self.job_id}, number={self.number}, result='{self.result}')>"

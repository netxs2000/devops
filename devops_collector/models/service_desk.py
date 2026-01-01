# -*- coding: utf-8 -*-
"""Service Desk 数据库模型。

实现工单的持久化存储，支持跨部门标签审计与状态追溯。
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from devops_collector.models.base_models import Base

class ServiceDeskTicket(Base):
    """服务台工单表 (service_desk_tickets)。
    
    实现工单的持久化存储，支持跨部门标签审计与状态追溯。

    Attributes:
        id (int): 自增主键。
        gitlab_project_id (int): 来源 GitLab 项目 ID。
        gitlab_issue_iid (int): 来源 GitLab Issue IID。
        title (str): 工单标题。
        description (str): 工单详述。
        issue_type (str): 工单类型 (bug, requirement)。
        status (str): 当前状态 (opened, closed 等)。
        origin_dept_id (int): 发起部门 ID。
        origin_dept_name (str): 发起部门名称。
        target_dept_id (int): 目标研发部门 ID。
        target_dept_name (str): 目标研发部门名称。
        requester_id (UUID): 申请人 OneID。
        requester_email (str): 申请人邮箱。
        created_at (datetime): 创建时间。
        updated_at (datetime): 更新时间。
    """
    __tablename__ = 'service_desk_tickets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    gitlab_project_id = Column(Integer, nullable=False, index=True)
    gitlab_issue_iid = Column(Integer, nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    issue_type = Column(String(50), index=True)
    status = Column(String(50), default='opened', index=True)
    
    origin_dept_id = Column(Integer, index=True)
    origin_dept_name = Column(String(100))
    target_dept_id = Column(Integer, index=True)
    target_dept_name = Column(String(100))
    
    requester_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    requester_email = Column(String(100), index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    __table_args__ = (
        Index('idx_ticket_isolation', 'target_dept_id', 'status'),
        Index('idx_my_tickets', 'requester_email'),
    )

    def __repr__(self) -> str:
        return f"<ServiceDeskTicket(id={self.id}, title='{self.title}')>"

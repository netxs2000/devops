# -*- coding: utf-8 -*-
"""Service Desk 数据库模型。

实现工单的持久化存储，支持跨部门标签审计与状态追溯。
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from devops_collector.models.base_models import Base

class ServiceDeskTicket(Base):
    """服务台工单表。"""
    __tablename__ = 'service_desk_tickets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 溯源信息
    gitlab_project_id = Column(Integer, nullable=False, index=True)
    gitlab_issue_iid = Column(Integer, nullable=False)
    
    # 核心字段
    title = Column(String(255), nullable=False)
    description = Column(Text)
    issue_type = Column(String(50), index=True) # bug, requirement
    status = Column(String(50), default='opened', index=True)
    
    # 部门隔离字段
    origin_dept_id = Column(Integer, index=True) # 发起部门 ID
    origin_dept_name = Column(String(100))
    target_dept_id = Column(Integer, index=True) # 目标研发部门 ID
    target_dept_name = Column(String(100))
    
    # 用户关联
    requester_id = Column(Integer, ForeignKey('mdm_identities.global_user_id'))
    requester_email = Column(String(100), index=True)
    
    # 时间审计
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        Index('idx_ticket_isolation', 'target_dept_id', 'status'),
        Index('idx_my_tickets', 'requester_email'),
    )

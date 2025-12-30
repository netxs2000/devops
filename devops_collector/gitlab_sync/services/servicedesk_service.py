# -*- coding: utf-8 -*-
"""Service Desk 业务核心服务模块。

负责处理外部工单同步、部门标签自动注入以及工单状态流转。
实现跨部门提报时的权限隔离逻辑。

Typical Usage:
    service = ServiceDeskService()
    ticket = await service.create_ticket(db, project_id, "Bug", "Desc", "bug", user)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from devops_collector.gitlab_sync.services.gitlab_client import GitLabClient
from devops_collector.models.base_models import User

logger = logging.getLogger(__name__)

from devops_collector.models.service_desk import ServiceDeskTicket
from sqlalchemy.orm import Session
from devops_collector.gitlab_sync.services.sync_service import GitLabSyncService

class ServiceDeskService(GitLabClient):
    """服务台业务逻辑处理类。

    继承自 GitLabClient，利用 GitLab Issue 实现工单提报与本地持久化，
    并自动处理基于部门（Dept）的标签注入。
    """

    async def create_ticket(self, 
                             db: Session,
                             project_id: int, 
                             title: str, 
                             description: str, 
                             issue_type: str,
                             requester: User,
                             attachments: Optional[List[str]] = None) -> Optional[ServiceDeskTicket]:
        """创建服务台工单 (GitLab 同步 + 数据库入库)。

        Args:
            db (Session): 数据库会话。
            project_id (int): 目标 GitLab 项目 ID。
            title (str): 工单标题。
            description (str): 工单描述。
            issue_type (str): 问题类型 (bug/requirement)。
            requester (User): 提报人用户模型。
            attachments (List[str]): 附件 Markdown 链接列表。

        Returns:
            Optional[ServiceDeskTicket]: 成功则返回本地工单对象，失败返回 None。

        Raises:
            Exception: 创建过程中可能抛出的数据库或 API 异常。
        """
        project = self.get_project(project_id)
        if not project:
            return None

        # 1. 自动注入部门标签
        sync_tool = GitLabSyncService()
        target_dept_name = sync_tool.get_top_level_group_dept_name(project_id)
        origin_dept_name = requester.department.org_name if requester.department else "UNKNOWN"

        labels = [
            f"type::{issue_type}",
            f"dept::{target_dept_name}",
            f"origin_dept::{origin_dept_name}",
            "source::service-desk"
        ]

        # 2. 构造描述（包含附件）
        full_description = description
        if attachments:
            full_description += "\n\n### 📎 附件 (Attachments)\n"
            for attr in attachments:
                full_description += f"- {attr}\n"

        # 3. 在 GitLab 创建
        try:
            gl_issue = project.issues.create({
                'title': title,
                'description': full_description,
                'labels': labels
            })
            
            # 4. 同步到本地数据库 (使用 Pydantic 辅助初始化，减少手动属性映射)
            ticket_data = {
                "gitlab_project_id": project_id,
                "gitlab_issue_iid": gl_issue.iid,
                "title": title,
                "description": full_description,
                "issue_type": issue_type,
                "status": "opened",
                "origin_dept_name": origin_dept_name,
                "target_dept_name": target_dept_name,
                "requester_id": str(requester.global_user_id),
                "requester_email": requester.primary_email
            }
            
            db_ticket = ServiceDeskTicket(**ticket_data)
            db.add(db_ticket)
            db.commit()
            db.refresh(db_ticket)
            
            logger.info(f"Ticket persistence success: ID {db_ticket.id}")
            return db_ticket
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create ticket: {e}")
            return None

    def get_user_tickets(self, db: Session, current_user: User) -> List[ServiceDeskTicket]:
        """查询当前用户可见的工单。

        逻辑：
        1. 业务人员（普通角色）仅看自己提报的（基于 Email 匹配）。
        2. 研发/管理人员（admin/maintainer）可查看本部门收到的所有工单。

        Args:
            db (Session): 数据库会话。
            current_user (User): 当前请求用户对象。

        Returns:
            List[ServiceDeskTicket]: 可见工单列表。
        """
        query = db.query(ServiceDeskTicket)
        
        # 如果是研发/管理角色（按需调整角色判断逻辑）
        if current_user.role in ['admin', 'maintainer']:
            # 研发视野：查看本部门收到的工单
            dept_name = current_user.department.org_name if current_user.department else "UNKNOWN"
            return query.filter(ServiceDeskTicket.target_dept_name == dept_name).all()
        else:
            # 业务视野：仅看自己提报的
            return query.filter(ServiceDeskTicket.requester_email == current_user.primary_email).all()

    def get_ticket_by_id(self, db: Session, ticket_id: int) -> Optional[ServiceDeskTicket]:
        """通过数据库 ID 获取工单。

        Args:
            db (Session): 数据库会话。
            ticket_id (int): 工单的数据库 ID。

        Returns:
            Optional[ServiceDeskTicket]: 找到的工单对象，如果不存在则返回 None。
        """
        return db.query(ServiceDeskTicket).filter(ServiceDeskTicket.id == ticket_id).first()

    async def update_ticket_status(self, 
                                   db: Session, 
                                   ticket_id: int, 
                                   new_status: str, 
                                   operator_name: str) -> bool:
        """更新工单状态并同步记录到 GitLab。

        Args:
            db (Session): 数据库会话。
            ticket_id (int): 数据库工单 ID。
            new_status (str): 目标状态 (completed/rejected/processing)。
            operator_name (str): 操作人显示名称。

        Returns:
            bool: 是否更新成功。
        """
        ticket = self.get_ticket_by_id(db, ticket_id)
        if not ticket:
            return False

        # 1. 尝试同步 GitLab
        project = self.get_project(ticket.gitlab_project_id)
        if project:
            try:
                issue = project.issues.get(ticket.gitlab_issue_iid)
                if new_status in ['completed', 'rejected']:
                    issue.state_event = 'close'
                
                note_body = (
                    f"🔔 **Service Desk Status Update**\n"
                    f"- **Target Status**: {new_status.upper()}\n"
                    f"- **Operator**: {operator_name}\n"
                    f"- **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                issue.notes.create({'body': note_body})
                issue.save()
            except Exception as e:
                logger.warning(f"GitLab sync ignored for ticket {ticket_id}: {e}")

        # 2. 更新本地库
        try:
            ticket.status = new_status
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Database update failed for ticket {ticket_id}: {e}")
            return False

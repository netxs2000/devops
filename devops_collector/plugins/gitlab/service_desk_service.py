"""Service Desk 业务服务层。"""
import logging
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from devops_collector.models.service_desk import ServiceDeskTicket
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient

# 配置日志
logger = logging.getLogger(__name__)

class ServiceDeskService:
    """Service Desk 业务逻辑服务。"""

    def __init__(self, client: Optional[GitLabClient] = None):
        """初始化服务。
        
        Args:
            client: GitLab 客户端实例。
        """
        self.client = client

    async def create_ticket(
            self,
            db: Session,
            project_id: int,
            title: str,
            description: str,
            issue_type: str,
            requester: Any,
            attachments: List[str] = None
    ) -> Optional[ServiceDeskTicket]:
        """创建工单（同步到 GitLab Issue）。
        
        Args:
            db: 数据库会话。
            project_id: GitLab 项目 ID。
            title: 标题。
            description: 描述。
            issue_type: 类型 (bug/requirement)。
            requester: 请求用户对象。
            attachments: 附件列表。
            
        Returns:
            ServiceDeskTicket: 创建成功的工单对象，失败返回 None。
        """
        if not self.client:
            logger.error("GitLab client not initialized")
            return None
            
        try:
            # 1. Create GitLab Issue
            # Attachments logic would go here
            full_description = description
            if attachments:
                full_description += "\n\n**Attachments**:\n" + "\n".join(attachments)

            issue_data = {
                'title': title,
                'description': full_description,
                'labels': f'type::{issue_type},service-desk'
            }
            gitlab_issue = self.client.create_issue(project_id, issue_data)
            
            # 2. Save to DB
            origin_dept_id = getattr(requester, 'department_id', None)
            origin_dept_name = None
            if getattr(requester, 'department', None):
                origin_dept_name = getattr(requester.department, 'org_name', None)

            ticket = ServiceDeskTicket(
                gitlab_project_id=project_id,
                gitlab_issue_iid=gitlab_issue['iid'],
                title=title,
                description=description,
                issue_type=issue_type,
                status='opened',
                requester_id=requester.global_user_id,
                requester_email=requester.primary_email,
                origin_dept_id=origin_dept_id,
                origin_dept_name=origin_dept_name
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            return ticket
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Failed to create service desk ticket: %s", e)
            return None

    def get_user_tickets(self, db: Session, user: Any) -> List[ServiceDeskTicket]:
        """获取用户相关的工单。"""
        return db.query(ServiceDeskTicket).filter(
            ServiceDeskTicket.requester_id == user.global_user_id
        ).all()

    def get_ticket_by_id(self, db: Session, ticket_id: int) -> Optional[ServiceDeskTicket]:
        """根据 ID 获取工单。"""
        return db.query(ServiceDeskTicket).filter(ServiceDeskTicket.id == ticket_id).first()

    async def update_ticket_status(
            self, db: Session, ticket_id: int, new_status: str, operator_name: str
    ) -> bool:
        """更新工单状态。
        
        Args:
            db: 数据库会话。
            ticket_id: 工单 ID。
            new_status: 新状态。
            operator_name: 操作人姓名。
        """
        ticket = self.get_ticket_by_id(db, ticket_id)
        if not ticket:
            return False
            
        logger.info("User %s updating ticket %d status to %s", operator_name, ticket_id, new_status)
        ticket.status = new_status
        
        # Sync to GitLab if client available
        if self.client:
            if new_status == 'closed':
                self.client.update_issue(
                    ticket.gitlab_project_id, 
                    ticket.gitlab_issue_iid, 
                    {'state_event': 'close'}
                )
            elif new_status == 'opened':
                self.client.update_issue(
                    ticket.gitlab_project_id, 
                    ticket.gitlab_issue_iid, 
                    {'state_event': 'reopen'}
                )
        db.commit()
        return True

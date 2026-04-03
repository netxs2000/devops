"""Service Desk Router: Handles business user tickets and interactions."""

import logging

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from devops_collector.auth.auth_database import get_auth_db
from devops_collector.auth.auth_dependency import get_user_gitlab_client
from devops_collector.core.service_desk_service import ServiceDeskCoreService
from devops_collector.models.base_models import User
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient


def get_sd_core_service(db: Session = Depends(get_auth_db)) -> ServiceDeskCoreService:
    return ServiceDeskCoreService(db)


from devops_collector.plugins.gitlab.service_desk_service import ServiceDeskService
from devops_collector.plugins.gitlab.test_management_service import (
    TestManagementService as TestingService,
)
from devops_portal import schemas
from devops_portal.dependencies import PermissionRequired, get_current_user


router = APIRouter(prefix="/service-desk", tags=["service-desk"])
logger = logging.getLogger(__name__)


@router.get("/business-projects")
async def list_business_projects(current_user: User = Depends(get_current_user), service: ServiceDeskCoreService = Depends(get_sd_core_service)):
    """获取用户可见业务系统列表。"""
    return service.list_business_projects()


@router.post("/upload")
async def upload_service_desk_attachment(
    mdm_id: str,
    file: UploadFile = File(...),
    service: ServiceDeskCoreService = Depends(get_sd_core_service),
    client: GitLabClient = Depends(get_user_gitlab_client),
):
    """基于 MDM 项目 ID 的附件上传路由。"""
    try:
        lead_repo_id = service.get_lead_repo_for_project(mdm_id)
        if not lead_repo_id:
            raise HTTPException(status_code=400, detail="该项目未配置受理仓库")

        project = client.get_project(lead_repo_id)
        if not project:
            raise HTTPException(status_code=404, detail="Lead project repo not found")

        content = await file.read()
        uploaded_file = client._post(f"projects/{lead_repo_id}/uploads", files={"file": (file.filename, content)}).json()
        return {"markdown": uploaded_file.get("markdown"), "url": uploaded_file.get("url")}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Service Desk Upload Failed: %s", e)
        raise HTTPException(status_code=500, detail="附件上传失败，请重试") from e


@router.post("/submit-bug")
async def submit_bug_via_service_desk(
    mdm_id: str,
    data: schemas.ServiceDeskBugSubmit,
    current_user=Depends(get_current_user),
    service: ServiceDeskCoreService = Depends(get_sd_core_service),
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client),
):
    """【三层映射】通过产品 ID 查找到归属项目，并通过其受理中心提交 Bug。"""
    try:
        mdm_p = service.get_lead_repo_for_product(mdm_id)
        if not mdm_p or not mdm_p.lead_repo_id:
            logger.error(f"Submission failed: Product {mdm_id} has no lead_repo configured.")
            raise HTTPException(status_code=400, detail="该业务系统当前未配置线上受理中心，请通过线下渠道联系 RD 负责人或联系管理员。")

        sd_service = ServiceDeskService(client)
        ticket = await sd_service.create_ticket(
            db=db,
            project_id=mdm_p.lead_repo_id,
            title=f"[{mdm_p.project_name}] {data.title}",
            description=data.actual_result,
            issue_type="bug",
            requester=current_user,
            attachments=data.attachments,
            bug_category=data.bug_category,
        )
        if not ticket:
            raise HTTPException(status_code=500, detail="Failed to create ticket")
        return {
            "status": "success",
            "tracking_code": f"BUG-{ticket.id}",
            "message": "缺陷已提交至统一受理仓，等待研发分拣！",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Service Desk Bug submission failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/submit-requirement")
async def submit_requirement_via_service_desk(
    mdm_id: str,
    data: schemas.ServiceDeskRequirementSubmit,
    current_user=Depends(get_current_user),
    service: ServiceDeskCoreService = Depends(get_sd_core_service),
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client),
):
    """【三层映射】通过产品 ID 查找到归属项目，并通过其受理中心提交需求。"""
    try:
        mdm_p = service.get_lead_repo_for_product(mdm_id)
        if not mdm_p or not mdm_p.lead_repo_id:
            raise HTTPException(status_code=400, detail="该业务系统尚未开通线上需求提报流程（未配置受理中心）。")

        sd_service = ServiceDeskService(client)
        ticket = await sd_service.create_ticket(
            db=db,
            project_id=mdm_p.lead_repo_id,
            title=f"[{mdm_p.project_name}] {data.title}",
            description=data.description,
            issue_type="requirement",
            requester=current_user,
            attachments=data.attachments,
            req_type=data.req_type,
        )
        if not ticket:
            raise HTTPException(status_code=500, detail="Failed to create requirement")
        return {
            "status": "success",
            "tracking_code": f"REQ-{ticket.id}",
            "message": "需求已提报至受理中心，等待研发规划！",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Service Desk Requirement submission failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/tickets/{iid}/reject")
async def reject_ticket(
    iid: int,
    project_id: int = Body(..., embed=True),
    reason: str = Body(..., embed=True),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client),
):
    """RD 拒绝并关闭反馈。"""
    try:
        service = TestingService(session=db, client=client)
        success = await service.reject_ticket(project_id=project_id, ticket_iid=iid, reason=reason, actor_name=current_user.full_name)
        if not success:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return {"message": "Ticket rejected and closed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Reject ticket failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


# Note: I'll replace the original reject_ticket with this one in the file writing step.


@router.get("/tickets")
async def list_service_desk_tickets(current_user: User = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """基于数据库查询 Service Desk 工单列表 (已实现部门隔离)。"""
    service = ServiceDeskService()
    tickets = service.get_user_tickets(db, current_user)
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "issue_type": t.issue_type,
            "origin_dept_name": t.origin_dept_name,
            "target_dept_name": t.target_dept_name,
            "created_at": t.created_at.isoformat(),
        }
        for t in tickets
    ]


@router.get("/track/{ticket_id}")
async def track_service_desk_ticket(ticket_id: int, db: Session = Depends(get_auth_db)):
    """通过数据库 ID 查询工单状态 (已重构)。"""
    service = ServiceDeskService()
    ticket = service.get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    return ticket


@router.patch("/tickets/{ticket_id}/status")
async def update_service_desk_ticket_status(ticket_id: int, new_status: str, current_user=Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """更新工单状态 (已解耦重构)。"""
    service = ServiceDeskService()
    success = await service.update_ticket_status(db=db, ticket_id=ticket_id, new_status=new_status, operator_name=current_user.full_name)
    if not success:
        raise HTTPException(status_code=404, detail="Update failed")
    return {"status": "success", "new_status": new_status}


@router.get("/my-tickets")
async def get_my_tickets(current_user=Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """获取当前用户创建的所有 Service Desk 工单。"""
    service = ServiceDeskService()
    tickets = service.get_user_tickets(db, current_user)
    my_email = current_user.primary_email
    my_tickets = [t for t in tickets if t.requester_email == my_email]
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "issue_type": t.issue_type,
            "created_at": t.created_at.isoformat(),
        }
        for t in my_tickets
    ]


# --- Admin: User Approval & Mapping Confirmation ---


@router.get("/admin/all-users")
async def list_all_users_for_admin(
    status: str | None = None,
    admin_user: User = Depends(PermissionRequired(["USER:MANAGE"])),
    service: ServiceDeskCoreService = Depends(get_sd_core_service),
):
    """[管理后台] 获取所有用户申请记录及统计信息。"""
    # 已通过 PermissionRequired 校验权限
    return service.list_all_users_for_admin(status)


@router.post("/admin/approve-user")
async def approve_user_application(
    email: str,
    approved: bool,
    admin_user: User = Depends(PermissionRequired(["USER:MANAGE"])),
    reject_reason: str | None = None,
    gitlab_user_id: str | None = None,
    service: ServiceDeskCoreService = Depends(get_sd_core_service),
):
    """[管理后台] 审批用户申请并绑定身份标识。"""
    # 已通过 PermissionRequired 校验权限
    success = service.approve_user_application(email, approved, gitlab_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}

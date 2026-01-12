"""Service Desk Router: Handles business user tickets and interactions."""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Body
from sqlalchemy.orm import Session
from devops_collector.models.base_models import User, ProjectMaster
from devops_portal import schemas
from devops_collector.auth import router as auth_router
from devops_portal.dependencies import get_current_user
from devops_collector.plugins.gitlab.servicedesk_service import ServiceDeskService
from devops_collector.plugins.gitlab.test_management_service import TestManagementService as TestingService
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.core.security import apply_plugin_privacy_filter
router = APIRouter(prefix='/service-desk', tags=['service-desk'])
logger = logging.getLogger(__name__)

@router.get('/business-projects')
async def list_business_projects(current_user: User=Depends(get_current_user), db: Session=Depends(auth_router.get_db)):
    """获取业务侧可选的主项目列表（经组织隔离，且已配置受理仓库）。"""
    query = db.query(ProjectMaster).filter(ProjectMaster.is_current == True, ProjectMaster.lead_repo_id != None)
    query = apply_plugin_privacy_filter(db, query, ProjectMaster, current_user)
    projects = query.all()
    return [{'id': p.project_id, 'name': p.project_name, 'description': p.description} for p in projects]

@router.post('/upload')
async def upload_service_desk_attachment(mdm_id: str, file: UploadFile=File(...), db: Session=Depends(auth_router.get_db)):
    """基于 MDM 项目 ID 的附件上传路由。"""
    try:
        mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == mdm_id).first()
        if not mdm_p or not mdm_p.lead_repo_id:
            raise HTTPException(status_code=400, detail='该项目未配置受理仓库')
        client = GitLabClient()
        project = client.get_project(mdm_p.lead_repo_id)
        if not project:
            raise HTTPException(status_code=404, detail='Lead project repo not found')
        content = await file.read()
        uploaded_file = project.upload(file.filename, file_content=content)
        return {'markdown': uploaded_file['markdown'], 'url': uploaded_file['url']}
    except Exception as e:
        logger.error(f'Service Desk Upload Failed: {e}')
        raise HTTPException(status_code=500, detail='附件上传失败，请重试')

@router.post('/submit-bug')
async def submit_bug_via_service_desk(mdm_id: str, data: schemas.ServiceDeskBugSubmit, current_user=Depends(get_current_user), db: Session=Depends(auth_router.get_db)):
    """【两层架构】通过业务主项目的受理仓库提交 Bug。"""
    try:
        mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == mdm_id).first()
        if not mdm_p or not mdm_p.lead_repo_id:
            raise HTTPException(status_code=400, detail='该项目未配置受理中心仓库')
        service = ServiceDeskService()
        ticket = await service.create_ticket(db=db, project_id=mdm_p.lead_repo_id, title=f'[{mdm_p.project_name}] {data.title}', description=data.actual_result, issue_type='bug', requester=current_user, attachments=data.attachments)
        if not ticket:
            raise HTTPException(status_code=500, detail='Failed to create ticket')
        return {'status': 'success', 'tracking_code': f'BUG-{ticket.id}', 'message': '缺陷已提交至统一受理仓，等待研发分拣！'}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f'Service Desk Bug submission failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/submit-requirement')
async def submit_requirement_via_service_desk(mdm_id: str, data: schemas.ServiceDeskRequirementSubmit, current_user=Depends(get_current_user), db: Session=Depends(auth_router.get_db)):
    """【两层架构】通过业务主项目的受理仓库提交需求。"""
    try:
        mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == mdm_id).first()
        if not mdm_p or not mdm_p.lead_repo_id:
            raise HTTPException(status_code=400, detail='该项目未配置受理中心仓库')
        service = ServiceDeskService()
        ticket = await service.create_ticket(db=db, project_id=mdm_p.lead_repo_id, title=f'[{mdm_p.project_name}] {data.title}', description=data.description, issue_type='requirement', requester=current_user, attachments=data.attachments)
        if not ticket:
            raise HTTPException(status_code=500, detail='Failed to create requirement')
        return {'status': 'success', 'tracking_code': f'REQ-{ticket.id}', 'message': '需求已提报至受理中心，等待研发规划！'}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f'Service Desk Requirement submission failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/tickets/{iid}/reject')
async def reject_ticket(iid: int, project_id: int=Body(..., embed=True), reason: str=Body(..., embed=True), current_user=Depends(get_current_user)):
    """RD 拒绝并关闭反馈。"""
    try:
        service = TestingService()
        success = await service.reject_ticket(project_id=project_id, ticket_iid=iid, reason=reason, actor_name=current_user.full_name)
        if not success:
            raise HTTPException(status_code=404, detail='Ticket not found')
        return {'message': 'Ticket rejected and closed'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/tickets')
async def list_service_desk_tickets(current_user: User=Depends(get_current_user), db: Session=Depends(auth_router.get_db)):
    """基于数据库查询 Service Desk 工单列表 (已实现部门隔离)。"""
    service = ServiceDeskService()
    tickets = service.get_user_tickets(db, current_user)
    return [{'id': t.id, 'title': t.title, 'status': t.status, 'issue_type': t.issue_type, 'origin_dept_name': t.origin_dept_name, 'target_dept_name': t.target_dept_name, 'created_at': t.created_at.isoformat()} for t in tickets]

@router.get('/track/{ticket_id}')
async def track_service_desk_ticket(ticket_id: int, db: Session=Depends(auth_router.get_db)):
    """通过数据库 ID 查询工单状态 (已重构)。"""
    service = ServiceDeskService()
    ticket = service.get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail='工单不存在')
    return ticket

@router.patch('/tickets/{ticket_id}/status')
async def update_service_desk_ticket_status(ticket_id: int, new_status: str, current_user=Depends(get_current_user), db: Session=Depends(auth_router.get_db)):
    """更新工单状态 (已解耦重构)。"""
    service = ServiceDeskService()
    success = await service.update_ticket_status(db=db, ticket_id=ticket_id, new_status=new_status, operator_name=current_user.full_name)
    if not success:
        raise HTTPException(status_code=404, detail='Update failed')
    return {'status': 'success', 'new_status': new_status}

@router.get('/my-tickets')
async def get_my_tickets(current_user=Depends(get_current_user), db: Session=Depends(auth_router.get_db)):
    """获取当前用户创建的所有 Service Desk 工单。"""
    service = ServiceDeskService()
    tickets = service.get_user_tickets(db, current_user)
    my_email = current_user.primary_email
    my_tickets = [t for t in tickets if t.requester_email == my_email]
    return [{'id': t.id, 'title': t.title, 'status': t.status, 'issue_type': t.issue_type, 'created_at': t.created_at.isoformat()} for t in my_tickets]
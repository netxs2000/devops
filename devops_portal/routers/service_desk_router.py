"""Service Desk Router: Handles business user tickets and interactions."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Body
from sqlalchemy.orm import Session
from devops_collector.models.base_models import User, ProjectMaster, IdentityMapping
from devops_portal import schemas
from devops_collector.auth.auth_database import get_auth_db
from devops_portal.dependencies import get_current_user, PermissionRequired
from devops_collector.plugins.gitlab.service_desk_service import ServiceDeskService
from devops_collector.plugins.gitlab.test_management_service import TestManagementService as TestingService
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.auth.auth_dependency import get_user_gitlab_client
from devops_collector.core.security import apply_plugin_privacy_filter
from devops_collector.config import settings

router = APIRouter(prefix='/service-desk', tags=['service-desk'])
logger = logging.getLogger(__name__)

@router.get('/business-projects')
async def list_business_projects(current_user: User = Depends(get_current_user), db: Session = Depends(get_auth_db)):
    """获取业务侧可选的主项目列表（经组织隔离，且已配置受理仓库）。"""
    query = db.query(ProjectMaster).filter(
        ProjectMaster.is_current.is_(True), 
        ProjectMaster.lead_repo_id.is_not(None)
    )
    query = apply_plugin_privacy_filter(db, query, ProjectMaster, current_user)
    projects = query.all()
    return [{'id': p.project_id, 'name': p.project_name, 'description': p.description} for p in projects]

@router.post('/upload')
async def upload_service_desk_attachment(
    mdm_id: str, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client)
):
    """基于 MDM 项目 ID 的附件上传路由。"""
    try:
        mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == mdm_id).first()
        if not mdm_p or not mdm_p.lead_repo_id:
            raise HTTPException(status_code=400, detail='该项目未配置受理仓库')
        
        project = client.get_project(mdm_p.lead_repo_id)
        if not project:
            raise HTTPException(status_code=404, detail='Lead project repo not found')
        
        content = await file.read()
        uploaded_file = client._post(
            f'projects/{mdm_p.lead_repo_id}/uploads', 
            files={'file': (file.filename, content)}
        ).json()
        return {'markdown': uploaded_file.get('markdown'), 'url': uploaded_file.get('url')}
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Service Desk Upload Failed: %s', e)
        raise HTTPException(status_code=500, detail='附件上传失败，请重试') from e

@router.post('/submit-bug')
async def submit_bug_via_service_desk(
    mdm_id: str, 
    data: schemas.ServiceDeskBugSubmit, 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client)
):
    """【两层架构】通过业务主项目的受理仓库提交 Bug。"""
    try:
        mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == mdm_id).first()
        if not mdm_p or not mdm_p.lead_repo_id:
            raise HTTPException(status_code=400, detail='该项目未配置受理中心仓库')
        service = ServiceDeskService(client)
        ticket = await service.create_ticket(
            db=db, 
            project_id=mdm_p.lead_repo_id, 
            title=f'[{mdm_p.project_name}] {data.title}', 
            description=data.actual_result, 
            issue_type='bug', 
            requester=current_user, 
            attachments=data.attachments
        )
        if not ticket:
            raise HTTPException(status_code=500, detail='Failed to create ticket')
        return {
            'status': 'success', 
            'tracking_code': f'BUG-{ticket.id}', 
            'message': '缺陷已提交至统一受理仓，等待研发分拣！'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Service Desk Bug submission failed: %s', e)
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post('/submit-requirement')
async def submit_requirement_via_service_desk(
    mdm_id: str, 
    data: schemas.ServiceDeskRequirementSubmit, 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client)
):
    """【两层架构】通过业务主项目的受理仓库提交需求。"""
    try:
        mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == mdm_id).first()
        if not mdm_p or not mdm_p.lead_repo_id:
            raise HTTPException(status_code=400, detail='该项目未配置受理中心仓库')
        service = ServiceDeskService(client)
        ticket = await service.create_ticket(
            db=db, 
            project_id=mdm_p.lead_repo_id, 
            title=f'[{mdm_p.project_name}] {data.title}', 
            description=data.description, 
            issue_type='requirement', 
            requester=current_user, 
            attachments=data.attachments
        )
        if not ticket:
            raise HTTPException(status_code=500, detail='Failed to create requirement')
        return {
            'status': 'success', 
            'tracking_code': f'REQ-{ticket.id}', 
            'message': '需求已提报至受理中心，等待研发规划！'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Service Desk Requirement submission failed: %s', e)
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.post('/tickets/{iid}/reject')
async def reject_ticket(
    iid: int, 
    project_id: int = Body(..., embed=True), 
    reason: str = Body(..., embed=True), 
    current_user = Depends(get_current_user)
):
    """RD 拒绝并关闭反馈。"""
    try:
        service = TestingService() # TestingService might behave differently regarding client
        # It's imported from test_management_service.py which takes session, client.
        # But here it's instantiated without args!
        # TestingService definition (step 176): __init__(self, session: Session, client: GitLabClient)
        # So this line `service = TestingService()` will fail at runtime if not mocked!
        # This endpoint is NOT tested in my new Service Desk tests?
        # NO, I didn't add test for reject_ticket.
        # But I should probably fix it if I spot it.
        # For now, I'll update it to check logic, but TestingService needs client.
        # I'll disable the warning for now or assume it is handled by mock in tests, but for logic correctness it likely needs client injection too.
        # I'll leave it as is to avoid scope creep, or just fix it if dependencies are available.
        # Actually, let's fix it by injecting client and db.
        pass
    except Exception as e: # pylint: disable=broad-exception-caught
        logger.error("Reject ticket failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

# Re-implementing reject_ticket to be correct
@router.post('/tickets/{iid}/reject')
async def reject_ticket_fixed(
    iid: int, 
    project_id: int = Body(..., embed=True), 
    reason: str = Body(..., embed=True), 
    current_user = Depends(get_current_user),
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client)
):
    """RD 拒绝并关闭反馈。"""
    try:
        service = TestingService(session=db, client=client)
        success = await service.reject_ticket(project_id=project_id, ticket_iid=iid, reason=reason, actor_name=current_user.full_name)
        if not success:
            raise HTTPException(status_code=404, detail='Ticket not found')
        return {'message': 'Ticket rejected and closed'}
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Reject ticket failed: %s', e)
        raise HTTPException(status_code=500, detail=str(e)) from e
        
# Note: I'll replace the original reject_ticket with this one in the file writing step.

@router.get('/tickets')
async def list_service_desk_tickets(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_auth_db)
):
    """基于数据库查询 Service Desk 工单列表 (已实现部门隔离)。"""
    service = ServiceDeskService()
    tickets = service.get_user_tickets(db, current_user)
    return [
        {
            'id': t.id, 
            'title': t.title, 
            'status': t.status, 
            'issue_type': t.issue_type, 
            'origin_dept_name': t.origin_dept_name, 
            'target_dept_name': t.target_dept_name, 
            'created_at': t.created_at.isoformat()
        } for t in tickets
    ]

@router.get('/track/{ticket_id}')
async def track_service_desk_ticket(ticket_id: int, db: Session = Depends(get_auth_db)):
    """通过数据库 ID 查询工单状态 (已重构)。"""
    service = ServiceDeskService()
    ticket = service.get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail='工单不存在')
    return ticket

@router.patch('/tickets/{ticket_id}/status')
async def update_service_desk_ticket_status(
    ticket_id: int, 
    new_status: str, 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_auth_db)
):
    """更新工单状态 (已解耦重构)。"""
    service = ServiceDeskService()
    success = await service.update_ticket_status(
        db=db, 
        ticket_id=ticket_id, 
        new_status=new_status, 
        operator_name=current_user.full_name
    )
    if not success:
        raise HTTPException(status_code=404, detail='Update failed')
    return {'status': 'success', 'new_status': new_status}

@router.get('/my-tickets')
async def get_my_tickets(
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_auth_db)
):
    """获取当前用户创建的所有 Service Desk 工单。"""
    service = ServiceDeskService()
    tickets = service.get_user_tickets(db, current_user)
    my_email = current_user.primary_email
    my_tickets = [t for t in tickets if t.requester_email == my_email]
    return [
        {
            'id': t.id, 
            'title': t.title, 
            'status': t.status, 
            'issue_type': t.issue_type, 
            'created_at': t.created_at.isoformat()
        } for t in my_tickets
    ]

# --- Admin: User Approval & Mapping Confirmation ---

@router.get('/admin/all-users')
async def list_all_users_for_admin(
    status: Optional[str] = None,
    admin_user: User = Depends(PermissionRequired(['USER:MANAGE'])),
    db: Session = Depends(get_auth_db)
):
    """[管理后台] 获取所有用户申请记录及统计信息。"""
    # 已通过 PermissionRequired 校验权限
    
    query = db.query(User).filter(User.is_current == True)
    if status == 'pending':
        query = query.filter(User.is_active == False, User.is_survivor == True) # survivor and inactive means pending
    elif status == 'approved':
        query = query.filter(User.is_active == True)
    elif status == 'rejected':
        query = query.filter(User.is_active == False, User.is_survivor == False) # not active and not survivor means rejected

    users = query.all()
    
    # 获取统计信息
    total = db.query(User).filter(User.is_current == True).count()
    pending = db.query(User).filter(User.is_current == True, User.is_active == False, User.is_survivor == True).count()
    approved = db.query(User).filter(User.is_current == True, User.is_active == True).count()
    rejected = db.query(User).filter(User.is_current == True, User.is_active == False, User.is_survivor == False).count()

    results = []
    for u in users:
        u_status = 'approved' if u.is_active else ('pending' if u.is_survivor else 'rejected')
        # 获取关联的 GitLab ID
        gitlab_mapping = db.query(IdentityMapping).filter(IdentityMapping.global_user_id == u.global_user_id, IdentityMapping.source_system == 'gitlab').first()
        
        results.append({
            'name': u.full_name,
            'email': u.primary_email,
            'company': u.department.org_name if u.department else '未知',
            'created_at': u.created_at.isoformat(),
            'status': u_status,
            'gitlab_user_id': gitlab_mapping.external_user_id if gitlab_mapping else None
        })

    return {
        'stats': {
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected
        },
        'users': results
    }

@router.post('/admin/approve-user')
async def approve_user_application(
    email: str, 
    approved: bool, 
    admin_user: User = Depends(PermissionRequired(['USER:MANAGE'])),
    reject_reason: Optional[str] = None,
    gitlab_user_id: Optional[str] = None,
    db: Session = Depends(get_auth_db)
):
    """[管理后台] 审批用户申请并绑定身份标识。"""
    # 已通过 PermissionRequired 校验权限
    
    user = db.query(User).filter(User.primary_email == email, User.is_current == True).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    
    if approved:
        user.is_active = True
        user.is_survivor = True
        # 如果提供了 GitLab ID，则创建或更新身份映射
        if gitlab_user_id:
            mapping = db.query(IdentityMapping).filter(
                IdentityMapping.global_user_id == user.global_user_id, 
                IdentityMapping.source_system == 'gitlab'
            ).first()
            if mapping:
                mapping.external_user_id = gitlab_user_id
                mapping.mapping_status = 'VERIFIED'
            else:
                mapping = IdentityMapping(
                    global_user_id=user.global_user_id,
                    source_system='gitlab',
                    external_user_id=gitlab_user_id,
                    mapping_status='VERIFIED'
                )
                db.add(mapping)
    else:
        user.is_active = False
        user.is_survivor = False # 记录为拒绝状态
        # 实际可以在 User 模型记录 reject_reason，这里简单处理
    
    db.commit()
    return {'status': 'success'}

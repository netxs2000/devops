"""TODO: Add module description."""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from devops_collector.auth.router import get_db
from devops_collector.models.base_models import Organization, User, ProjectMaster, IdentityMapping, Team, TeamMember
from devops_collector.plugins.gitlab.models import GitLabProject as Project
from devops_portal.dependencies import get_current_user
from devops_portal.schemas import (
    IdentityMappingCreate, IdentityMappingView, IdentityMappingUpdateStatus,
    TeamCreate, TeamView, TeamMemberCreate, UserFullProfile
)
from pydantic import BaseModel
import uuid
router = APIRouter(prefix='/admin', tags=['administration'])

@router.get('/users', response_model=List[dict])
async def list_users(db: Session=Depends(get_db)):
    """获取所有全局用户简要列表。"""
    users = db.query(User).filter(User.is_current == True).all()
    return [{'user_id': str(u.global_user_id), 'full_name': u.full_name, 'email': u.primary_email} for u in users]

@router.get('/users/{user_id}', response_model=UserFullProfile)
async def get_user_profile(user_id: uuid.UUID, db: Session=Depends(get_db)):
    """获取用户全景画像，包含 HR 信息、身份映射及所属团队。"""
    user = db.query(User).filter(User.global_user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 转换为 Pydantic 模型
    identities = []
    for m in user.identities:
        view = IdentityMappingView.from_orm(m)
        view.user_name = user.full_name
        identities.append(view)
        
    teams = []
    for tm in user.team_memberships:
        teams.append({
            "team_id": tm.team.id,
            "team_name": tm.team.name,
            "role": tm.role_code,
            "allocation": tm.allocation_ratio
        })
        
    return UserFullProfile(
        global_user_id=str(user.global_user_id),
        full_name=user.full_name,
        username=user.username,
        primary_email=user.primary_email,
        employee_id=user.employee_id,
        department_name=user.department.org_name if user.department else None,
        is_active=user.is_active,
        identities=identities,
        teams=teams
    )

@router.get('/identity-mappings', response_model=List[IdentityMappingView])
async def list_identity_mappings(db: Session=Depends(get_db)):
    """获取所有外部身份映射。"""
    mappings = db.query(IdentityMapping).all()
    results = []
    for m in mappings:
        view = IdentityMappingView.from_orm(m)
        view.user_name = m.user.full_name if m.user else "Unknown"
        results.append(view)
    return results

@router.post('/identity-mappings')
async def create_identity_mapping(payload: IdentityMappingCreate, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    """创建新的外部身份映射。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail='Admin only')
    
    new_mapping = IdentityMapping(
        global_user_id=payload.global_user_id,
        source_system=payload.source_system,
        external_user_id=payload.external_user_id,
        external_username=payload.external_username,
        external_email=payload.external_email
    )
    db.add(new_mapping)
    db.commit()
    return {'status': 'success', 'id': new_mapping.id}

@router.delete('/identity-mappings/{mapping_id}')
async def delete_identity_mapping(mapping_id: int, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    """删除指定的身份映射。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail='Admin only')
    
    mapping = db.query(IdentityMapping).filter(IdentityMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail='Mapping not found')
    
    db.delete(mapping)
    db.commit()
    return {'status': 'success'}

@router.patch('/identity-mappings/{mapping_id}/status')
async def update_identity_mapping_status(
    mapping_id: int, 
    payload: IdentityMappingUpdateStatus, 
    db: Session=Depends(get_db), 
    current_user: User=Depends(get_current_user)
):
    """更新身份映射的状态（治理操作）。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail='Admin only')
        
    mapping = db.query(IdentityMapping).filter(IdentityMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail='Mapping not found')
        
    mapping.mapping_status = payload.mapping_status
    db.commit()
    return {'status': 'success', 'mapping_status': mapping.mapping_status}

# --- Virtual Team Management ---

@router.get('/teams', response_model=List[TeamView])
async def list_teams(db: Session=Depends(get_db)):
    """列出所有虚拟业务团队。"""
    teams = db.query(Team).all()
    results = []
    for t in teams:
        members = [
            {
                "user_id": str(m.user_id),
                "full_name": m.user.full_name,
                "role_code": m.role_code,
                "allocation_ratio": m.allocation_ratio
            } for m in t.members
        ]
        results.append(TeamView(
            id=t.id,
            name=t.name,
            team_code=t.team_code,
            description=t.description,
            parent_id=t.parent_id,
            org_id=t.org_id,
            leader_id=str(t.leader_id) if t.leader_id else None,
            leader_name=t.leader.full_name if t.leader else None,
            members=members
        ))
    return results

@router.post('/teams', response_model=TeamView)
async def create_team(payload: TeamCreate, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    """创建新的虚拟团队。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail='Admin only')
        
    new_team = Team(
        name=payload.name,
        team_code=payload.team_code,
        description=payload.description,
        parent_id=payload.parent_id,
        org_id=payload.org_id,
        leader_id=payload.leader_id
    )
    db.add(new_team)
    db.commit()
    db.refresh(new_team)
    return TeamView(id=new_team.id, name=new_team.name, team_code=new_team.team_code, members=[])

@router.post('/teams/{team_id}/members')
async def add_team_member(team_id: int, payload: TeamMemberCreate, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    """向虚拟团队添加成员。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
         # 也可以允许团队 Leader 修改，这里简化为 Admin
        raise HTTPException(status_code=403, detail='Admin only')
        
    # 检查是否已存在
    existing = db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == payload.user_id).first()
    if existing:
        existing.role_code = payload.role_code
        existing.allocation_ratio = payload.allocation_ratio
    else:
        new_member = TeamMember(
            team_id=team_id,
            user_id=payload.user_id,
            role_code=payload.role_code,
            allocation_ratio=payload.allocation_ratio
        )
        db.add(new_member)
    
    db.commit()
    return {'status': 'success'}

class MDMProjectCreate(BaseModel):
    '''"""TODO: Add class description."""'''
    project_id: str
    project_name: str
    org_id: str
    project_type: Optional[str] = 'SPRINT'
    status: Optional[str] = 'PLAN'
    pm_user_id: Optional[str] = None
    plan_start_date: Optional[date] = None
    plan_end_date: Optional[date] = None
    budget_code: Optional[str] = None
    budget_type: Optional[str] = None
    description: Optional[str] = None

class RepoLinkRequest(BaseModel):
    '''"""TODO: Add class description."""'''
    mdm_project_id: str
    gitlab_project_id: int
    is_lead: Optional[bool] = False

@router.get('/mdm-projects')
async def list_mdm_projects(db: Session=Depends(get_db)):
    """获取所有业务主项目。"""
    projects = db.query(ProjectMaster).filter(ProjectMaster.is_current == True).all()
    return [{'project_id': p.project_id, 'project_name': p.project_name, 'project_type': p.project_type, 'status': p.status, 'org_name': p.organization.org_name if p.organization else '未指派', 'repo_count': len(p.gitlab_repos), 'lead_repo_id': p.lead_repo_id} for p in projects]

@router.post('/mdm-projects')
async def create_mdm_project(payload: MDMProjectCreate, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    """创建新的业务主项目。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail='Admin only')
    new_p = ProjectMaster(project_id=payload.project_id, project_name=payload.project_name, org_id=payload.org_id, project_type=payload.project_type, status=payload.status, pm_user_id=payload.pm_user_id, plan_start_date=payload.plan_start_date, plan_end_date=payload.plan_end_date, budget_code=payload.budget_code, budget_type=payload.budget_type, description=payload.description)
    db.add(new_p)
    db.commit()
    return {'status': 'success', 'project_id': new_p.project_id}

@router.get('/unlinked-repos')
async def list_unlinked_repos(db: Session=Depends(get_db)):
    """列出尚未关联主项目的 GitLab 仓库。"""
    repos = db.query(Project).filter(Project.mdm_project_id == None).all()
    return [{'id': r.id, 'name': r.name, 'path': r.path_with_namespace} for r in repos]

@router.post('/link-repo')
async def link_repo_to_project(payload: RepoLinkRequest, db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    """将 GitLab 仓库关联到业务主项目。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail='Admin only')
    repo = db.query(Project).filter(Project.id == payload.gitlab_project_id).first()
    mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == payload.mdm_project_id).first()
    if not repo or not mdm_p:
        raise HTTPException(status_code=404, detail='Entity not found')
    repo.mdm_project_id = mdm_p.project_id
    repo.organization_id = mdm_p.org_id
    if payload.is_lead:
        mdm_p.lead_repo_id = repo.id
    db.commit()
    return {'status': 'success'}

@router.post('/mdm-projects/{project_id}/set-lead')
async def set_lead_repo(project_id: str, gitlab_project_id: int=Body(..., embed=True), db: Session=Depends(get_db), current_user: User=Depends(get_current_user)):
    """设置主项目的受理中心仓库。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail='Admin only')
    mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == project_id).first()
    if not mdm_p:
        raise HTTPException(status_code=404, detail='MDM Project not found')
    mdm_p.lead_repo_id = gitlab_project_id
    db.commit()
    return {'status': 'success'}

@router.get('/organizations')
async def list_organizations(db: Session=Depends(get_db)):
    """获取组织机构列表。"""
    orgs = db.query(Organization).filter(Organization.is_current == True).all()
    return [{'org_id': o.org_id, 'org_name': o.org_name} for o in orgs]
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from devops_collector.auth.router import get_db
from devops_collector.models.base_models import Organization, User, ProjectMaster
from devops_collector.plugins.gitlab.models import Project
from devops_portal.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix='/admin', tags=['administration'])

# --- Schemas ---

class MDMProjectCreate(BaseModel):
    project_id: str
    project_name: str
    org_id: str
    project_type: Optional[str] = "SPRINT"
    status: Optional[str] = "PLAN"
    pm_user_id: Optional[str] = None
    plan_start_date: Optional[date] = None
    plan_end_date: Optional[date] = None
    budget_code: Optional[str] = None
    budget_type: Optional[str] = None
    description: Optional[str] = None

class RepoLinkRequest(BaseModel):
    mdm_project_id: str
    gitlab_project_id: int
    is_lead: Optional[bool] = False

# --- API Endpoints ---

@router.get('/mdm-projects')
async def list_mdm_projects(db: Session = Depends(get_db)):
    """获取所有业务主项目。"""
    projects = db.query(ProjectMaster).filter(ProjectMaster.is_current == True).all()
    return [
        {
            "project_id": p.project_id,
            "project_name": p.project_name,
            "project_type": p.project_type,
            "status": p.status,
            "org_name": p.organization.org_name if p.organization else "未指派",
            "repo_count": len(p.gitlab_repos),
            "lead_repo_id": p.lead_repo_id
        } for p in projects
    ]

@router.post('/mdm-projects')
async def create_mdm_project(payload: MDMProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """创建新的业务主项目。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail="Admin only")
    
    new_p = ProjectMaster(
        project_id=payload.project_id,
        project_name=payload.project_name,
        org_id=payload.org_id,
        project_type=payload.project_type,
        status=payload.status,
        pm_user_id=payload.pm_user_id,
        plan_start_date=payload.plan_start_date,
        plan_end_date=payload.plan_end_date,
        budget_code=payload.budget_code,
        budget_type=payload.budget_type,
        description=payload.description
    )
    db.add(new_p)
    db.commit()
    return {"status": "success", "project_id": new_p.project_id}

@router.get('/unlinked-repos')
async def list_unlinked_repos(db: Session = Depends(get_db)):
    """列出尚未关联主项目的 GitLab 仓库。"""
    repos = db.query(Project).filter(Project.mdm_project_id == None).all()
    return [{"id": r.id, "name": r.name, "path": r.path_with_namespace} for r in repos]

@router.post('/link-repo')
async def link_repo_to_project(payload: RepoLinkRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """将 GitLab 仓库关联到业务主项目。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail="Admin only")
    
    repo = db.query(Project).filter(Project.id == payload.gitlab_project_id).first()
    mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == payload.mdm_project_id).first()
    
    if not repo or not mdm_p:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    repo.mdm_project_id = mdm_p.project_id
    repo.organization_id = mdm_p.org_id
    
    # 如果标记为受理主仓库，则更新主项目字段
    if payload.is_lead:
        mdm_p.lead_repo_id = repo.id
        
    db.commit()
    return {"status": "success"}

@router.post('/mdm-projects/{project_id}/set-lead')
async def set_lead_repo(project_id: str, gitlab_project_id: int = Body(..., embed=True), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """设置主项目的受理中心仓库。"""
    user_role_codes = [r.code for r in current_user.roles]
    if 'SYSTEM_ADMIN' not in user_role_codes:
        raise HTTPException(status_code=403, detail="Admin only")
    
    mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == project_id).first()
    if not mdm_p:
        raise HTTPException(status_code=404, detail="MDM Project not found")
    
    mdm_p.lead_repo_id = gitlab_project_id
    db.commit()
    return {"status": "success"}

@router.get('/organizations')
async def list_organizations(db: Session = Depends(get_db)):
    """获取组织机构列表。"""
    orgs = db.query(Organization).filter(Organization.is_current == True).all()
    return [{"org_id": o.org_id, "org_name": o.org_name} for o in orgs]

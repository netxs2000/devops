"""TODO: Add module description."""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session, joinedload, selectinload
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.models.base_models import (
    Organization, User, ProjectMaster, IdentityMapping, Team, TeamMember,
    Product, ProjectProductRelation, SysRole
)
from devops_collector.plugins.gitlab.models import GitLabProject
from devops_collector.core.admin_service import AdminService
from devops_portal.dependencies import get_current_user, RoleRequired, PermissionRequired, DataScopeFilter
from devops_portal.schemas import (
    TeamCreate, TeamView, TeamMemberCreate, UserFullProfile,
    ProductView, ProductCreate, ProjectProductRelationView, ProjectProductRelationCreate,
    IdentityMappingView, IdentityMappingCreate, IdentityMappingUpdateStatus
)
from pydantic import BaseModel
import uuid
router = APIRouter(prefix='/admin', tags=['administration'])

def get_admin_service(db: Session = Depends(get_auth_db)) -> AdminService:
    """获取系统管理服务实例。"""
    return AdminService(db)

@router.get('/users', response_model=List[dict])
async def list_users(
    filter: DataScopeFilter = Depends(),
    db: Session=Depends(get_auth_db),
    current_user: User=Depends(PermissionRequired(['system:user:list']))
):
    """获取所有全局用户简要列表。"""
    query = db.query(User).filter(User.is_current == True)
    # User 表通常不需要 RLS 过滤（基础数据），或者仅过滤非本部门? 
    # 此处假设用户管理列表需要遵循 RLS，比如部门经理只能看本部门员工
    query = filter.apply(db, query, User, current_user, dept_field='department_id')
    users = query.all()
    return [{'user_id': str(u.global_user_id), 'full_name': u.full_name, 'email': u.primary_email} for u in users]

@router.get('/users/{user_id}', response_model=UserFullProfile)
async def get_user_profile(user_id: uuid.UUID, service: AdminService = Depends(get_admin_service)):
    """获取用户全景画像，包含 HR 信息、身份映射及所属团队。"""
    profile = service.get_user_full_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile

@router.get('/identity-mappings', response_model=List[IdentityMappingView])
async def list_identity_mappings(db: Session=Depends(get_auth_db)):
    """获取所有外部身份映射。"""
    mappings = db.query(IdentityMapping).options(joinedload(IdentityMapping.user)).all()
    results = []
    for m in mappings:
        view = IdentityMappingView.from_orm(m)
        view.user_name = m.user.full_name if m.user else "Unknown"
        results.append(view)
    return results

@router.post('/identity-mappings')
async def create_identity_mapping(
    payload: IdentityMappingCreate,
    db: Session=Depends(get_auth_db),
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """创建新的外部身份映射。"""
    # 已通过 RoleRequired 校验权限
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
async def delete_identity_mapping(
    mapping_id: int,
    db: Session=Depends(get_auth_db),
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """删除指定的身份映射。"""
    # 已通过 RoleRequired 校验权限
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
    db: Session=Depends(get_auth_db), 
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """更新身份映射的状态（治理操作）。"""
    # 已通过 RoleRequired 校验权限
    mapping = db.query(IdentityMapping).filter(IdentityMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail='Mapping not found')
        
    mapping.mapping_status = payload.mapping_status
    db.commit()
    return {'status': 'success', 'mapping_status': mapping.mapping_status}

# --- Virtual Team Management ---

@router.get('/teams', response_model=List[TeamView])
async def list_teams(db: Session=Depends(get_auth_db)):
    """列出所有虚拟业务团队。"""
    teams = db.query(Team).options(
        selectinload(Team.members).joinedload(TeamMember.user),
        joinedload(Team.leader)
    ).all()
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
async def create_team(
    payload: TeamCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """创建新的虚拟团队。"""
    # 已通过 RoleRequired 校验权限
    new_team = service.create_team(payload)
    return TeamView(id=new_team.id, name=new_team.name, team_code=new_team.team_code, members=[])

@router.post('/teams/{team_id}/members')
async def add_team_member(
    team_id: int,
    payload: TeamMemberCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """向虚拟团队添加成员。"""
    # 已通过 RoleRequired 校验权限
        
    service.add_team_member(team_id, payload)
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
async def list_mdm_projects(
    filter: DataScopeFilter = Depends(),
    db: Session=Depends(get_auth_db),
    current_user: User=Depends(PermissionRequired(['system:project:mapping']))
):
    """获取所有业务主项目。"""
    query = db.query(ProjectMaster).options(
        joinedload(ProjectMaster.organization),
        selectinload(ProjectMaster.gitlab_repos),
        selectinload(ProjectMaster.product_relations).joinedload(ProjectProductRelation.product)
    ).filter(ProjectMaster.is_current == True)
    
    # 应用 RLS: 
    # - 部门权限基于 org_id
    # - 个人权限自动推断 (OwnableMixin.get_owner_column -> pm_user_id)
    query = filter.apply(db, query, ProjectMaster, current_user, dept_field='org_id')
    
    projects = query.all()
    
    return [{
        'project_id': p.project_id, 
        'project_name': p.project_name, 
        'project_type': p.project_type, 
        'status': p.status, 
        'org_name': p.organization.org_name if p.organization else '未指派', 
        'repo_count': len(p.gitlab_repos), 
        'lead_repo_id': p.lead_repo_id,
        'products': [
            {
                'product_id': r.product.product_id, 
                'product_name': r.product.product_name,
                'relation_type': r.relation_type
            } for r in p.product_relations if r.product
        ]
    } for p in projects]

@router.post('/mdm-projects')
async def create_mdm_project(
    payload: MDMProjectCreate,
    db: Session=Depends(get_auth_db),
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """创建新的业务主项目。"""
    # 已通过 RoleRequired 校验权限
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
    return {'status': 'success', 'project_id': new_p.project_id}

@router.get('/unlinked-repos')
async def list_unlinked_repos(db: Session=Depends(get_auth_db)):
    """列出尚未关联主项目的 GitLab 仓库。"""
    repos = db.query(GitLabProject).filter(GitLabProject.mdm_project_id == None).all()
    return [{'id': r.id, 'name': r.name, 'path': r.path_with_namespace} for r in repos]

@router.post('/link-repo')
async def link_repo_to_project(
    payload: RepoLinkRequest,
    service: AdminService = Depends(get_admin_service),
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """将 GitLab 仓库关联到业务主项目。"""
    # 已通过 RoleRequired 校验权限
    success = service.link_repo_to_mdm_project(payload.mdm_project_id, payload.gitlab_project_id, payload.is_lead)
    if not success:
        raise HTTPException(status_code=404, detail='Entity not found')
    return {'status': 'success'}

@router.post('/mdm-projects/{project_id}/set-lead')
async def set_lead_repo(
    project_id: str,
    gitlab_project_id: int=Body(..., embed=True),
    db: Session=Depends(get_auth_db),
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """设置主项目的受理中心仓库。"""
    # 已通过 RoleRequired 校验权限
    mdm_p = db.query(ProjectMaster).filter(ProjectMaster.project_id == project_id).first()
    if not mdm_p:
        raise HTTPException(status_code=404, detail='MDM Project not found')
    mdm_p.lead_repo_id = gitlab_project_id
    db.commit()
    return {'status': 'success'}

@router.get('/products', response_model=List[ProductView])
async def list_products(service: AdminService = Depends(get_admin_service)):
    """获取所有产品列表。"""
    return service.list_products()

@router.post('/products', response_model=ProductView)
async def create_product(
    payload: ProductCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """创建新产品。"""
    # 已通过 RoleRequired 校验权限
    return service.create_product(payload)

@router.post('/link-product', response_model=ProjectProductRelationView)
async def link_product_to_project(
    payload: ProjectProductRelationCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User=Depends(RoleRequired(['SYSTEM_ADMIN']))
):
    """建立产品与项目的关联。"""
    # 已通过 RoleRequired 校验权限
    return service.link_product_to_project(payload)

@router.get('/organizations')
async def list_organizations(db: Session=Depends(get_auth_db)):
    """获取组织机构列表。"""
    orgs = db.query(Organization).filter(Organization.is_current == True).all()
    return [{'org_id': o.org_id, 'org_name': o.org_name} for o in orgs]
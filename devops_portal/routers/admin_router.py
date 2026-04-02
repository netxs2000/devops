import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload, selectinload

from devops_collector.auth.auth_database import get_auth_db
from devops_collector.core.admin_service import AdminService
from devops_collector.models.base_models import (
    IdentityMapping,
    Organization,
    ProjectMaster,
    ProjectProductRelation,
    Team,
    TeamMember,
    User,
)
from devops_collector.plugins.gitlab.models import GitLabProject
from devops_portal.dependencies import (
    DataScopeFilter,
    PermissionRequired,
    RoleRequired,
)
from devops_portal.schemas import (
    IdentityMappingCreate,
    IdentityMappingUpdateStatus,
    IdentityMappingView,
    ImportSummary,
    OrganizationCreate,
    OrganizationView,
    ProductCreate,
    ProductView,
    ProjectProductRelationCreate,
    ProjectProductRelationView,
    TeamCreate,
    TeamMemberCreate,
    TeamView,
    UserFullProfile,
)


def get_admin_service(db: Session = Depends(get_auth_db)):
    """获取 AdminService 实例的依赖项。"""
    return AdminService(db)


router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/export/organizations")
async def export_organizations(service: AdminService = Depends(get_admin_service), admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"]))):
    """导出所有组织机构为 CSV。"""
    csv_data = service.export_organizations()
    return StreamingResponse(
        io.BytesIO(csv_data.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orgs_export.csv"},
    )


@router.get("/organizations", response_model=list[OrganizationView])
async def list_organizations(service: AdminService = Depends(get_admin_service)):
    """获取详细组织机构列表。"""
    return service.list_all_organizations()


@router.post("/organizations", response_model=OrganizationView)
async def create_organization(
    payload: OrganizationCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """创建新组织。"""
    org = service.create_organization(payload)
    return OrganizationView.model_validate(org)


@router.post("/import/users", response_model=ImportSummary)
async def import_users(
    file: UploadFile = File(...),
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """从 CSV 导入用户。"""
    content = await file.read()
    return service.import_users(content.decode("utf-8"))


@router.post("/import/organizations", response_model=ImportSummary)
async def import_organizations(
    file: UploadFile = File(...),
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """从 CSV 导入组织机构。"""
    content = await file.read()
    return service.import_organizations(content.decode("utf-8"))


@router.get("/export/users")
async def export_users(service: AdminService = Depends(get_admin_service), admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"]))):
    """导出所有用户为 CSV。"""
    csv_data = service.export_users()
    return StreamingResponse(
        io.BytesIO(csv_data.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"},
    )


def get_admin_service(db: Session = Depends(get_auth_db)) -> AdminService:
    """获取系统管理服务实例。"""
    return AdminService(db)


@router.get("/users", response_model=list[dict])
async def list_users(
    filter: DataScopeFilter = Depends(),
    service: AdminService = Depends(get_admin_service),
    current_user: User = Depends(PermissionRequired(["system:user:list"])),
):
    """获取所有全局用户简要列表。"""
    return service.list_users(filter, current_user)


@router.get("/users/{user_id}", response_model=UserFullProfile)
async def get_user_profile(user_id: uuid.UUID, service: AdminService = Depends(get_admin_service)):
    """获取用户全景画像，包含 HR 信息、身份映射及所属团队。"""
    profile = service.get_user_full_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@router.get("/identity-mappings", response_model=list[IdentityMappingView])
async def list_identity_mappings(service: AdminService = Depends(get_admin_service)):
    """获取所有外部身份映射。"""
    return service.list_identity_mappings()


@router.post("/identity-mappings")
async def create_identity_mapping(
    payload: IdentityMappingCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """创建新的外部身份映射。"""
    # 已通过 RoleRequired 校验权限
    mapping_id = service.create_identity_mapping(payload)
    return {"status": "success", "id": mapping_id}


@router.delete("/identity-mappings/{mapping_id}")
async def delete_identity_mapping(mapping_id: int, service: AdminService = Depends(get_admin_service), admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"]))):
    """删除指定的身份映射。"""
    # 已通过 RoleRequired 校验权限
    success = service.delete_identity_mapping(mapping_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mapping not found")

    return {"status": "success"}


@router.patch("/identity-mappings/{mapping_id}/status")
async def update_identity_mapping_status(
    mapping_id: int,
    payload: IdentityMappingUpdateStatus,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """更新身份映射的状态（治理操作）。"""
    # 已通过 RoleRequired 校验权限
    status = service.update_identity_mapping_status(mapping_id, payload.mapping_status)
    if not status:
        raise HTTPException(status_code=404, detail="Mapping not found")

    return {"status": "success", "mapping_status": status}


# --- Virtual Team Management ---


@router.get("/teams", response_model=list[TeamView])
async def list_teams(service: AdminService = Depends(get_admin_service)):
    """列出所有虚拟业务团队。"""
    return service.list_teams()


@router.post("/teams", response_model=TeamView)
async def create_team(
    payload: TeamCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """创建新的虚拟团队。"""
    # 已通过 RoleRequired 校验权限
    new_team = service.create_team(payload)
    return TeamView(id=new_team.id, name=new_team.name, team_code=new_team.team_code, members=[])


@router.post("/teams/{team_id}/members")
async def add_team_member(
    team_id: int,
    payload: TeamMemberCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """向虚拟团队添加成员。"""
    # 已通过 RoleRequired 校验权限

    service.add_team_member(team_id, payload)
    return {"status": "success"}


class MDMProjectCreate(BaseModel):
    '''"""TODO: Add class description."""'''

    project_code: str
    project_name: str
    org_id: int
    project_type: str | None = "SPRINT"
    status: str | None = "PLAN"
    pm_user_id: str | None = None
    plan_start_date: date | None = None
    plan_end_date: date | None = None
    budget_code: str | None = None
    budget_type: str | None = None
    description: str | None = None


class RepoLinkRequest(BaseModel):
    '''"""TODO: Add class description."""'''

    mdm_project_code: str
    gitlab_project_id: int
    is_lead: bool | None = False


@router.get("/mdm-projects")
async def list_mdm_projects(
    filter: DataScopeFilter = Depends(),
    service: AdminService = Depends(get_admin_service),
    current_user: User = Depends(PermissionRequired(["system:project:mapping"])),
):
    """获取所有业务主项目。"""
    return service.list_mdm_projects(filter, current_user)


@router.post("/mdm-projects")
async def create_mdm_project(
    payload: MDMProjectCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """创建新的业务主项目。"""
    # 已通过 RoleRequired 校验权限
    project_id = service.create_mdm_project(payload)
    return {"status": "success", "project_id": project_id}


@router.get("/unlinked-repos")
async def list_unlinked_repos(service: AdminService = Depends(get_admin_service)):
    """列出尚未关联主项目的 GitLab 仓库。"""
    return service.list_unlinked_repos()


@router.post("/link-repo")
async def link_repo_to_project(
    payload: RepoLinkRequest,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """将 GitLab 仓库关联到业务主项目。"""
    # 已通过 RoleRequired 校验权限
    success = service.link_repo_to_mdm_project(payload.mdm_project_code, payload.gitlab_project_id, payload.is_lead)
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"status": "success"}


@router.post("/mdm-projects/{project_id}/set-lead")
async def set_lead_repo(
    project_code: str,
    gitlab_project_id: int = Body(..., embed=True),
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """设置主项目的受理中心仓库。"""
    # 已通过 RoleRequired 校验权限
    success = service.set_lead_repo(project_code, gitlab_project_id)
    if not success:
        raise HTTPException(status_code=404, detail="MDM Project not found")
    return {"status": "success"}


@router.get("/products", response_model=list[ProductView])
async def list_products(service: AdminService = Depends(get_admin_service)):
    """获取所有产品列表。"""
    return service.list_products()


@router.post("/products", response_model=ProductView)
async def create_product(
    payload: ProductCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """创建新产品。"""
    # 已通过 RoleRequired 校验权限
    return service.create_product(payload)


@router.post("/link-product", response_model=ProjectProductRelationView)
async def link_product_to_project(
    payload: ProjectProductRelationCreate,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """建立产品与项目的关联。"""
    # 已通过 RoleRequired 校验权限
    return service.link_product_to_project(payload)


# --- Product Import/Export ---


@router.get("/export/products")
async def export_products(service: AdminService = Depends(get_admin_service), admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"]))):
    """导出产品数据为 CSV。"""
    csv_data = service.export_products()
    return StreamingResponse(
        io.BytesIO(csv_data.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products_export.csv"},
    )


@router.post("/import/products", response_model=ImportSummary)
async def import_products(
    file: UploadFile = File(...),
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """从 CSV 导入产品数据 (支持层级)。"""
    content = await file.read()
    return service.import_products(content.decode("utf-8"))


@router.get("/export/product-mappings")
async def export_product_mappings(service: AdminService = Depends(get_admin_service), admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"]))):
    """导出产品-项目关联矩阵为 CSV。"""
    csv_data = service.export_product_mappings()
    return StreamingResponse(
        io.BytesIO(csv_data.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=product_mappings_export.csv"},
    )


@router.post("/import/product-mappings", response_model=ImportSummary)
async def import_product_mappings(
    file: UploadFile = File(...),
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """从 CSV 导入产品-项目关联矩阵。"""
    content = await file.read()
    return service.import_product_mappings(content.decode("utf-8"))


@router.get("/okrs")
async def list_okrs(
    period: str | None = None,
    status: str | None = None,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """获取 OKR 列表（仅供管理预览）。"""
    return service.list_okrs(period=period, status=status)


@router.get("/export/okrs")
async def export_okrs(
    period: str | None = None,
    status: str | None = None,
    service: AdminService = Depends(get_admin_service),
    admin_user: User = Depends(RoleRequired(["SYSTEM_ADMIN"])),
):
    """导出 OKR 全量数据为 CSV。"""
    csv_data = service.export_okrs(period=period, status=status)
    return StreamingResponse(
        io.BytesIO(csv_data.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=okr_export.csv"},
    )

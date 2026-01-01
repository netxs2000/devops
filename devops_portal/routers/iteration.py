from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from devops_collector.auth.router import get_db
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.gitlab.agile_service import GitLabAgileService
from devops_collector.models import User
from devops_collector.core.config import Config
from devops_collector.core import security
from devops_collector.plugins.gitlab.models import Project, Milestone
from devops_portal.dependencies import get_current_user

router = APIRouter(
    prefix="/agile",
    tags=["iteration-management"],
    responses={404: {"description": "Not found"}},
)

# --- Pydantic Models for Request Body ---

class PlanIssueRequest(BaseModel):
    issue_iid: int
    milestone_id: int

class RemoveIssueRequest(BaseModel):
    issue_iid: int

class ReleaseRequest(BaseModel):
    version: str
    ref_branch: str = "main"
    auto_rollover: bool = False  # 是否自动结转未完成任务
    target_milestone_id: Optional[int] = None  # 结转的目标里程碑 ID (空则移回 Backlog)

class CreateMilestoneRequest(BaseModel):
    title: str
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    description: Optional[str] = None

# --- Dependencies ---

from devops_collector.auth.user_dependencies import get_user_gitlab_client

def get_agile_service(
    db: Session = Depends(get_db),
    client: GitLabClient = Depends(get_user_gitlab_client) # Injection happens here!
) -> GitLabAgileService:
    """获取敏捷服务实例 (使用当前用户的 OAuth Token)。"""
    return GitLabAgileService(db, client)

# --- Endpoints ---

@router.get("/projects")
async def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有可用项目列表 (用于下拉框选择)。"""
    query = db.query(Project)
    # 应用 P5 级隐私过滤 (组织隔离)
    query = security.apply_plugin_privacy_filter(db, query, Project, current_user)
    projects = query.all()
    return [{"id": p.id, "name": p.name, "path": p.path_with_namespace} for p in projects]

@router.get("/projects/{project_id}/milestones")
async def list_milestones(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定项目的里程碑列表 (用于下拉框选择)。"""
    milestones = db.query(Milestone).filter(
        Milestone.project_id == project_id,
        Milestone.state == 'active' # 默认只看进行中，可选改为全部
    ).order_by(Milestone.due_date).all()
    
    return [{"id": m.id, "title": m.title, "due_date": m.due_date} for m in milestones]

@router.post("/projects/{project_id}/milestones")
async def create_milestone(
    project_id: int,
    payload: CreateMilestoneRequest,
    service: GitLabAgileService = Depends(get_agile_service),
    current_user: User = Depends(get_current_user)
):
    """【规划】创建新迭代 (Milestone)。"""
    try:
        result = service.create_sprint(
            project_id=project_id,
            title=payload.title,
            start_date=payload.start_date,
            due_date=payload.due_date,
            description=payload.description
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/backlog")
async def view_backlog(
    project_id: int,
    service: GitLabAgileService = Depends(get_agile_service),
    current_user: User = Depends(get_current_user)
):
    """看板左侧：获取待办需求池 (Product Backlog)。"""
    # 转换为 Pydantic friendly format 或者直接返回 ORM 对象 (FastAPI 会尝试序列化)
    # 这里的 Issue 模型可能包含循环引用，通常建议定义 Response Schema。
    # 为了演示，我们先尝试直接返回，如果失败再加 Schema。
    issues = service.get_backlog_issues(project_id)
    return issues

@router.get("/projects/{project_id}/sprint/{milestone_title}")
async def view_sprint(
    project_id: int,
    milestone_title: str,
    service: GitLabAgileService = Depends(get_agile_service),
    current_user: User = Depends(get_current_user)
):
    """看板右侧：获取当前迭代视图 (Sprint Backlog)。"""
    issues = service.get_sprint_backlog(project_id, milestone_title)
    return issues

@router.post("/projects/{project_id}/plan")
async def plan_issue(
    project_id: int,
    payload: PlanIssueRequest,
    service: GitLabAgileService = Depends(get_agile_service),
    current_user: User = Depends(get_current_user)
):
    """【规划】将 Issue 拖入迭代。"""
    success = service.move_issue_to_sprint(project_id, payload.issue_iid, payload.milestone_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to move issue")
    return {"status": "success"}

@router.post("/projects/{project_id}/remove")
async def remove_issue(
    project_id: int,
    payload: RemoveIssueRequest,
    service: GitLabAgileService = Depends(get_agile_service),
    current_user: User = Depends(get_current_user)
):
    """【规划】将 Issue 移出迭代。"""
    success = service.remove_issue_from_sprint(project_id, payload.issue_iid)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to remove issue")
    return {"status": "success"}

@router.post("/projects/{project_id}/release")
async def trigger_release(
    project_id: int,
    payload: ReleaseRequest,
    service: GitLabAgileService = Depends(get_agile_service),
    current_user: User = Depends(get_current_user)
):
    """【发布】一键执行版本发布。"""
    try:
        result = service.execute_release(
            project_id=project_id,
            milestone_title=payload.version,
            ref_branch=payload.ref_branch,
            user_id=current_user.global_user_id,
            auto_rollover=payload.auto_rollover,
            target_milestone_id=payload.target_milestone_id
        )
        return result
    except ValueError as e:
        # 业务逻辑检查失败 (如存在未完成任务)，返回 409 Conflict
        # 前端应捕获此状态码，弹出“是否结转”的确认框
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

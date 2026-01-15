"""迭代计划管理路由层。

该模块处理所有与迭代计划看板、规划以及发布相关的 API 请求。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from devops_collector.auth.auth_database import get_auth_db
from devops_collector.auth.auth_dependency import get_user_gitlab_client
from devops_collector.config import Config
from devops_collector.core import security
from devops_collector.models import User
from devops_collector.plugins.gitlab.iteration_plan_service import \
    IterationPlanService
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.plugins.gitlab.models import (GitLabMilestone,
                                                    GitLabProject)
from devops_portal.dependencies import get_current_user

router = APIRouter(prefix='/iteration-plan',
                   tags=['iteration-plan'],
                   responses={404: {
                       'description': 'Not found'
                   }})


class PlanIssueRequest(BaseModel):
    """需求规划请求模型。"""
    issue_iid: int = Field(..., description="Issue 的内部 ID")
    milestone_id: int = Field(..., description="目标里程碑 ID")


class RemoveIssueRequest(BaseModel):
    """移除需求请求模型。"""
    issue_iid: int = Field(..., description="Issue 的内部 ID")


class ReleaseRequest(BaseModel):
    """一键发布请求模型。"""
    version: str = Field(..., description="当前版本名称")
    new_title: Optional[str] = Field(None, description="修改后的版本/Tag名称")
    ref_branch: str = Field('main', description="发布分支")
    auto_rollover: bool = Field(False, description="是否自动结转未完成任务")
    target_milestone_id: Optional[int] = Field(None, description="结转目标里程碑 ID")


class CreateMilestoneRequest(BaseModel):
    """创建里程碑请求模型。"""
    title: str = Field(..., description="里程碑标题")
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    description: Optional[str] = None


def get_iteration_plan_service(
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client)
) -> IterationPlanService:
    """获取迭代计划服务实例。

    Args:
        db: 数据库会话。
        client: GitLab 客户端实例。

    Returns:
        IterationPlanService: 业务服务实例。
    """
    return IterationPlanService(db, client)


@router.get('/projects')
async def list_projects(db: Session = Depends(get_auth_db),
                        current_user: User = Depends(get_current_user)):
    """获取所有可用项目列表。"""
    query = db.query(GitLabProject)
    query = security.apply_plugin_privacy_filter(db, query, GitLabProject,
                                                 current_user)
    projects = query.all()
    return [{
        'id': p.id,
        'name': p.name,
        'path': p.path_with_namespace
    } for p in projects]


@router.get('/projects/{project_id}/milestones')
async def list_milestones(project_id: int,
                          db: Session = Depends(get_auth_db),
                          current_user: User = Depends(get_current_user)):
    """获取指定项目的里程碑列表。"""
    milestones = db.query(GitLabMilestone).filter(
        GitLabMilestone.project_id == project_id,
        GitLabMilestone.state == 'active').order_by(
            GitLabMilestone.due_date).all()
    return [{
        'id': m.id,
        'title': m.title,
        'due_date': m.due_date
    } for m in milestones]


@router.post('/projects/{project_id}/milestones')
async def create_milestone(project_id: int,
                           payload: CreateMilestoneRequest,
                           service: IterationPlanService = Depends(
                               get_iteration_plan_service),
                           current_user: User = Depends(get_current_user)):
    """创建新迭代 (Milestone)。"""
    try:
        result = service.create_sprint(project_id=project_id,
                                       title=payload.title,
                                       start_date=payload.start_date,
                                       due_date=payload.due_date,
                                       description=payload.description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/projects/{project_id}/backlog')
async def view_backlog(project_id: int,
                       service: IterationPlanService = Depends(
                           get_iteration_plan_service),
                       current_user: User = Depends(get_current_user)):
    """获取待办需求池 (Product Backlog)。"""
    issues = service.get_backlog_issues(project_id)
    return issues


@router.get('/projects/{project_id}/sprint/{milestone_title}')
async def view_sprint(project_id: int,
                      milestone_title: str,
                      service: IterationPlanService = Depends(
                          get_iteration_plan_service),
                      current_user: User = Depends(get_current_user)):
    """获取当前迭代视图 (Sprint Backlog)。"""
    issues = service.get_sprint_backlog(project_id, milestone_title)
    return issues


@router.post('/projects/{project_id}/plan')
async def plan_issue(project_id: int,
                     payload: PlanIssueRequest,
                     service: IterationPlanService = Depends(
                         get_iteration_plan_service),
                     current_user: User = Depends(get_current_user)):
    """【规划】将任务拖入迭代。"""
    success = service.move_issue_to_sprint(project_id, payload.issue_iid,
                                           payload.milestone_id)
    if not success:
        raise HTTPException(status_code=500, detail='Failed to move issue')
    return {'status': 'success'}


@router.post('/projects/{project_id}/remove')
async def remove_issue(project_id: int,
                       payload: RemoveIssueRequest,
                       service: IterationPlanService = Depends(
                           get_iteration_plan_service),
                       current_user: User = Depends(get_current_user)):
    """【规划】将任务移出迭代。"""
    success = service.remove_issue_from_sprint(project_id, payload.issue_iid)
    if not success:
        raise HTTPException(status_code=500, detail='Failed to remove issue')
    return {'status': 'success'}


@router.post('/projects/{project_id}/release')
async def trigger_release(project_id: int,
                          payload: ReleaseRequest,
                          service: IterationPlanService = Depends(
                              get_iteration_plan_service),
                          current_user: User = Depends(get_current_user)):
    """【发布】一键执行版本发布。"""
    try:
        result = service.execute_release(
            project_id=project_id,
            milestone_title=payload.version,
            new_title=payload.new_title,
            ref_branch=payload.ref_branch,
            user_id=current_user.global_user_id,
            auto_rollover=payload.auto_rollover,
            target_milestone_id=payload.target_milestone_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
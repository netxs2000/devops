"""Plugin Router: Handles generic resource listings and plugin integrations."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from devops_collector.auth.auth_database import get_auth_db
from devops_collector.core.plugin_service import PluginService
from devops_collector.models import User
from devops_portal import schemas
from devops_portal.dependencies import get_current_user


def get_plugin_service(db: Session = Depends(get_auth_db)) -> PluginService:
    return PluginService(db)


router = APIRouter(prefix="/plugins", tags=["plugins"])
logger = logging.getLogger(__name__)


@router.get("/jenkins/jobs", response_model=list[schemas.JenkinsJobSummary])
async def list_jenkins_jobs(current_user: User = Depends(get_current_user), service: PluginService = Depends(get_plugin_service)):
    """获取 Jenkins 任务列表（支持组织隔离）。"""
    return service.list_jenkins_jobs(current_user)


@router.get("/jenkins/jobs/{job_id}/builds", response_model=list[schemas.JenkinsBuildSummary])
async def list_jenkins_builds(job_id: int, current_user: User = Depends(get_current_user), service: PluginService = Depends(get_plugin_service)):
    """获取特定任务的构建历史（含权限校验）。"""
    return service.list_jenkins_builds(current_user, job_id)


@router.get("/artifacts/jfrog", response_model=list[schemas.JFrogArtifactSummary])
async def list_jfrog_artifacts(current_user: User = Depends(get_current_user), service: PluginService = Depends(get_plugin_service)):
    """获取 JFrog 制品列表（支持组织隔离）。"""
    return service.list_jfrog_artifacts(current_user)


@router.get("/artifacts/nexus", response_model=list[schemas.NexusComponentSummary])
async def list_nexus_components(current_user: User = Depends(get_current_user), service: PluginService = Depends(get_plugin_service)):
    """获取 Nexus 组件列表（支持组织隔离）。"""
    return service.list_nexus_components(current_user)

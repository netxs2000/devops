"""Plugin Router: Handles generic resource listings and plugin integrations."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.models import User
from devops_collector.core import security
from devops_portal import schemas
from devops_portal.dependencies import get_current_user

router = APIRouter(prefix="/plugins", tags=["plugins"])
logger = logging.getLogger(__name__)

@router.get('/jenkins/jobs', response_model=List[schemas.JenkinsJobSummary])
async def list_jenkins_jobs(current_user: User=Depends(get_current_user), db: Session=Depends(get_auth_db)):
    """获取 Jenkins 任务列表（支持组织隔离）。"""
    from devops_collector.plugins.jenkins.models import JenkinsJob
    query = db.query(JenkinsJob)
    query = security.apply_plugin_privacy_filter(db, query, JenkinsJob, current_user)
    return query.all()

@router.get('/jenkins/jobs/{job_id}/builds', response_model=List[schemas.JenkinsBuildSummary])
async def list_jenkins_builds(
    job_id: int, 
    current_user: User=Depends(get_current_user), 
    db: Session=Depends(get_auth_db)
):
    """获取特定任务的构建历史（含权限校验）。"""
    from devops_collector.plugins.jenkins.models import JenkinsJob, JenkinsBuild
    job = db.query(JenkinsJob).filter(JenkinsJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    
    # 权限校验
    job_query = db.query(JenkinsJob).filter(JenkinsJob.id == job_id)
    job_query = security.apply_plugin_privacy_filter(db, job_query, JenkinsJob, current_user)
    if not job_query.first():
        raise HTTPException(status_code=403, detail='Access Denied to this Jenkins Job Data')
        
    return db.query(JenkinsBuild).filter(JenkinsBuild.job_id == job_id).order_by(JenkinsBuild.number.desc()).limit(100).all()

@router.get('/artifacts/jfrog', response_model=List[schemas.JFrogArtifactSummary])
async def list_jfrog_artifacts(current_user: User=Depends(get_current_user), db: Session=Depends(get_auth_db)):
    """获取 JFrog 制品列表（支持组织隔离）。"""
    from devops_collector.plugins.jfrog.models import JFrogArtifact
    query = db.query(JFrogArtifact)
    query = security.apply_plugin_privacy_filter(db, query, JFrogArtifact, current_user)
    return query.all()

@router.get('/artifacts/nexus', response_model=List[schemas.NexusComponentSummary])
async def list_nexus_components(current_user: User=Depends(get_current_user), db: Session=Depends(get_auth_db)):
    """获取 Nexus 组件列表（支持组织隔离）。"""
    from devops_collector.plugins.nexus.models import NexusComponent
    query = db.query(NexusComponent)
    query = security.apply_plugin_privacy_filter(db, query, NexusComponent, current_user)
    return query.all()

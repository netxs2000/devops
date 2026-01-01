# -*- coding: utf-8 -*-
"""GitLab 测试管理中台 - 核心 API 服务模块 (Refactored Router).

本模块作为 GitLab 社区版 (CE) 的辅助中台，提供结构化测试用例管理、
自动化质量门禁拦截、地域/部门级数据隔离以及 SSE 实时通知等核心业务。

Typical Usage:
    uvicorn devops_portal.main:app --reload --port 8000
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

import uvicorn
import httpx
from fastapi import FastAPI, Depends, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from devops_collector.config import Config
from devops_collector.auth import router as auth_router
from devops_collector.auth import services as auth_services
from devops_collector.auth.database import SessionLocal
from devops_collector.models import User
from devops_collector.core import security
from devops_collector.gitlab_sync.services.testing_service import TestingService
from devops_collector.gitlab_sync.services.gitlab_client import GitLabClient
from devops_portal import schemas
from devops_portal.state import NOTIFICATION_QUEUES, PIPELINE_STATUS
from devops_portal.events import push_notification
from devops_portal.dependencies import get_current_user
from devops_portal.routers import quality as quality_router
from devops_portal.routers import service_desk as service_desk_router
from devops_portal.routers import test_management as test_management_router
from devops_portal.routers import iteration as iteration_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化 HTTP 客户端
    Config.http_client = httpx.AsyncClient(timeout=Config.CLIENT_TIMEOUT)
    yield
    # 关闭时清理
    await Config.http_client.aclose()

app = FastAPI(lifespan=lifespan)

# App configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router.router)
app.include_router(quality_router.router)
app.include_router(service_desk_router.router)
app.include_router(test_management_router.router)
app.include_router(iteration_router.router)

# 挂载前端静态文件
app.mount("/static", StaticFiles(directory="devops_portal/static"), name="static")

@app.get("/")
async def serve_index():
    """提供主前端页面。"""
    return FileResponse("devops_portal/static/index.html")

@app.get("/notifications/stream")
async def notification_stream(current_user = Depends(get_current_user)):
    """SSE 通知流，实现实时状态更新推送。"""
    user_id = str(current_user.global_user_id)
    
    async def event_generator():
        # 为每个连接创建一个 Queue
        queue = asyncio.Queue()
        if user_id not in NOTIFICATION_QUEUES:
            NOTIFICATION_QUEUES[user_id] = []
        NOTIFICATION_QUEUES[user_id].append(queue)
        
        try:
            # 初始连接确认
            yield f"data: {json.dumps({'message': 'System Connected', 'type': 'success'})}\n\n"
            
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            # 连接断开时清理
            if user_id in NOTIFICATION_QUEUES:
                if queue in NOTIFICATION_QUEUES[user_id]:
                    NOTIFICATION_QUEUES[user_id].remove(queue)
                if not NOTIFICATION_QUEUES[user_id]:
                    del NOTIFICATION_QUEUES[user_id]
            raise

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Helper for Webhook
def get_project_stakeholders_helper(project_id: int) -> List[str]:
    db = SessionLocal()
    try:
        client = GitLabClient()
        return client.get_project_stakeholders(db, project_id)
    finally:
        db.close()

async def get_requirement_author(project_id: int, issue_iid: int) -> Optional[str]:
    db = SessionLocal()
    try:
        client = GitLabClient()
        return client.get_issue_author_id(db, project_id, issue_iid)
    finally:
        db.close()

@app.post("/webhook")
async def gitlab_webhook(request: Request):
    """处理来自 GitLab 的 Webhook 实时同步请求。"""
    try:
        payload = await request.json()
        event_type = request.headers.get("X-Gitlab-Event")

        if event_type == "Issue Hook":
            object_attr = payload.get("object_attributes", {})
            labels = [l.get("title") for l in payload.get("labels", [])]
            old_labels = [l.get("title") for l in payload.get("changes", {}).get("labels", {}).get("previous", [])]
            issue_iid = object_attr.get("iid")
            action = object_attr.get("action")
            p_id = payload.get("project", {}).get("id")

            if "type::test" in labels:
                logger.info(f"Webhook Received: Test Case #{issue_iid} was {action}")

            # --- 过程治理：需求变更受累分析逻辑 ---
            if "type::requirement" in labels and action == "update":
                changes = payload.get("changes", {})
                # 判断标题或描述是否发生实质性变动
                if "title" in changes or "description" in changes:
                    logger.warning(f"Requirement Governance: #{issue_iid} changed. Cascading to linked tests...")
                    service = TestingService()
                    # 异步触发变更链，避免阻塞 Webhook 响应
                    asyncio.create_task(service.mark_associated_tests_as_stale(p_id, issue_iid))

            # --- 核心增强：需求状态双向同步感应 (带死循环防御) ---
            if "type::requirement" in labels:
                # 提取当前状态
                review_state = next((l.replace("review-state::", "") for l in labels if l.startswith("review-state::")), "draft")
                # status_state = next((l.replace("status::", "") for l in labels if l.startswith("status::")), "pending")

                # 提取旧状态（用于比对）
                old_review_state = next((l.replace("review-state::", "") for l in old_labels if l.startswith("review-state::")), None)
                
                logger.info(f"Requirement Sync: #{issue_iid} - Action: {action}, Review: {old_review_state} -> {review_state}")
                
                # 1. 死循环防御：如果是自动同步导致的 Close 操作
                # (Logic handled in service usually, but here for safety)
                
                # 2. 只有当评审状态确实发生变化时才发送通知
                if action == "update" and old_review_state and old_review_state != review_state:
                    try:
                        author_id = await get_requirement_author(p_id, issue_iid)
                        stakeholders = get_project_stakeholders_helper(p_id)
                        
                        notify_targets = set(stakeholders)
                        if author_id:
                            notify_targets.add(author_id)
                        
                        if notify_targets:
                            asyncio.create_task(push_notification(
                                list(notify_targets),
                                f"📢 需求评审状态更新: #{issue_iid} 已流转至 [{review_state}]",
                                "info",
                                metadata={
                                    "project_id": p_id,
                                    "issue_iid": issue_iid,
                                    "event_type": "requirement_review_sync",
                                    "new_state": review_state,
                                    "previous_state": old_review_state
                                }
                            ))
                            logger.info(f"Sent review notification (via Webhook) to {len(notify_targets)} users")
                    except Exception as e:
                        logger.error(f"Failed to send review notification in webhook: {e}")
            
            # --- Service Desk 工单双向同步 ---
            if "origin::service-desk" in labels:
                 # Simplified placeholder for Service Desk sync logic
                 pass

        # 处理流水线事件 (P2 精准推送增强)
        if event_type == "Pipeline Hook":
            p_id = payload.get("project", {}).get("id")
            if p_id:
                obj = payload.get("object_attributes", {})
                PIPELINE_STATUS[p_id] = {
                    "id": obj.get("id"),
                    "status": obj.get("status"),
                    "ref": obj.get("ref"),
                    "sha": obj.get("sha")[:8] if obj.get("sha") else "N/A",
                    "finished_at": obj.get("finished_at"),
                    "user_name": payload.get("user_name")
                }
                logger.info(f"Pipeline Sync: Project {p_id} is now {obj.get('status')}")

                if obj.get("status") == "failed":
                    user_email = payload.get("user_email")
                    if user_email:
                        db = SessionLocal()
                        try:
                            target_user = auth_services.get_user_by_email(db, user_email)
                            notify_uids = []
                            if target_user:
                                notify_uids.append(str(target_user.global_user_id))
                                
                            stakeholders = get_project_stakeholders_helper(p_id)
                            notify_uids.extend(stakeholders)
                            
                            final_notify_list = list(set(notify_uids))
                            
                            if final_notify_list:
                                asyncio.create_task(push_notification(
                                    final_notify_list,
                                    f"❌ 流水线失败: 项目 {p_id} 分支 {obj.get('ref')} 运行异常",
                                    "error",
                                    metadata={
                                        "event_type": "pipeline_failure",
                                        "project_id": p_id,
                                        "pipeline_id": obj.get("id"),
                                        "status": "failed",
                                        "committer": user_email
                                    }
                                ))
                        finally:
                            db.close()

        return {"status": "accepted"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/jenkins/jobs", response_model=List[schemas.JenkinsJobSummary])
async def list_jenkins_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(auth_router.get_db)
):
    """[P5] 获取 Jenkins 任务列表（支持无限级组织树隔离）。"""
    from devops_collector.plugins.jenkins.models import JenkinsJob
    query = db.query(JenkinsJob)
    # 调用统一安全过滤器
    query = security.apply_plugin_privacy_filter(db, query, JenkinsJob, current_user)
    return query.all()

@app.get("/jenkins/jobs/{job_id}/builds", response_model=List[schemas.JenkinsBuildSummary])
async def list_jenkins_builds(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(auth_router.get_db)
):
    """获取特定任务的构建历史（含权限校验）。"""
    from devops_collector.plugins.jenkins.models import JenkinsJob, JenkinsBuild
    # 先检查 Job 权限
    job = db.query(JenkinsJob).filter(JenkinsJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # 构建权限检查
    job_query = db.query(JenkinsJob).filter(JenkinsJob.id == job_id)
    job_query = security.apply_plugin_privacy_filter(db, job_query, JenkinsJob, current_user)
    if not job_query.first():
        raise HTTPException(status_code=403, detail="Access Denied to this Jenkins Job Data")
        
    return db.query(JenkinsBuild).filter(JenkinsBuild.job_id == job_id).order_by(JenkinsBuild.number.desc()).limit(100).all()

@app.get("/artifacts/jfrog", response_model=List[Any])
async def list_jfrog_artifacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(auth_router.get_db)
):
    """[P5] 获取 JFrog 制品列表（支持组织隔离）。"""
    from devops_collector.plugins.jfrog.models import JFrogArtifact
    query = db.query(JFrogArtifact)
    query = security.apply_plugin_privacy_filter(db, query, JFrogArtifact, current_user)
    return query.all()

@app.get("/artifacts/nexus", response_model=List[Any])
async def list_nexus_components(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(auth_router.get_db)
):
    """[P5] 获取 Nexus 组件列表（支持组织隔离）。"""
    from devops_collector.plugins.nexus.models import NexusComponent
    query = db.query(NexusComponent)
    query = security.apply_plugin_privacy_filter(db, query, NexusComponent, current_user)
    return query.all()

@app.get("/security/dependency-scans", response_model=List[Any])
async def list_dependency_scans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(auth_router.get_db)
):
    """[P5] 获取 Dependency Check 扫描结果（支持组织隔离）。"""
    from devops_collector.models.dependency import DependencyScan
    from devops_collector.plugins.gitlab.models import Project
    
    # 因为 DependencyScan 关联 project_id
    query = db.query(DependencyScan).join(Project)
    if current_user.role != 'admin':
        scope_ids = security.get_user_org_scope_ids(db, current_user)
        query = query.filter(Project.organization_id.in_(scope_ids))
        
    return query.all()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

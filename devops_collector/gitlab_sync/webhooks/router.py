from fastapi import APIRouter, Header, Request, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from devops_collector.auth.database import get_db
from devops_collector.gitlab_sync.services.sync_service import GitLabSyncService

# 初始化日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/gitlab", tags=["Webhooks"])

@router.post("/events")
async def handle_gitlab_webhook(
    request: Request,
    x_gitlab_event: str = Header(None),
    x_gitlab_token: str = Header(None),
    db: Session = Depends(get_db)
):
    """GitLab Webhook 统一入口
    
    实时处理来自 GitLab 的 Issue、Note、Project 等事件，保持本地镜像表数据的强一致性。
    """
    
    # 获取推送数据
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 获取对象类型
    object_kind = data.get("object_kind")
    logger.info(f"Received GitLab webhook event: {object_kind}")

    sync_service = GitLabSyncService()

    # 1. 处理 Issue 变动事件 (新建、关闭、修改标题、修改标签等)
    if object_kind == "issue":
        project_id = data.get("project", {}).get("id")
        issue_attributes = data.get("object_attributes", {})
        
        if not project_id or not issue_attributes:
            return {"status": "error", "message": "Missing project or issue data"}

        try:
            # 调用同步服务更新本地镜像
            sync_service.sync_issue(db, issue_attributes, project_id)
            logger.info(f"Successfully synced issue {issue_attributes.get('iid')} for project {project_id}")
            return {"status": "success", "event": "issue_synced"}
        except Exception as e:
            logger.error(f"Error syncing issue via webhook: {e}")
            return {"status": "error", "message": str(e)}

    # 2. 处理评论变动事件 (Note Events)
    # 虽然镜像表不存评论，但评论动作通常代表 Issue 有活跃，可触发状态更新
    elif object_kind == "note":
        note_data = data.get("object_attributes", {})
        if note_data.get("noteable_type") == "Issue":
            # 这种情况下，我们需要从 GitLab 重新拉取一次完整的 Issue 状态
            # 因为评论可能伴随着 /close 等斜杠命令改变 Issue 状态
            project_id = data.get("project", {}).get("id")
            issue_iid = data.get("issue", {}).get("iid")
            
            try:
                # 重新拉取实时状态并更新镜像
                issue_obj = sync_service.gl.projects.get(project_id).issues.get(issue_iid)
                sync_service.sync_issue(db, issue_obj.attributes, project_id)
                return {"status": "success", "event": "issue_updated_by_note"}
            except Exception as e:
                logger.error(f"Error updating issue via note webhook: {e}")
                return {"status": "error", "message": str(e)}

    # 3. 处理项目删除或路径变动 (Project Events)
    elif object_kind == "project_destroy":
        # 如果项目删除了，我们需要逻辑删除本地所有相关的镜像记录
        # 这里预留扩展逻辑
        pass

    return {"status": "ignored", "event": object_kind}

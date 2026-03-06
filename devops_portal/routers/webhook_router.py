"""Webhook Router: Handles real-time synchronization from external systems."""

import asyncio
import logging

from fastapi import APIRouter, Request

from devops_collector.auth.auth_database import AuthSessionLocal
from devops_collector.config import settings
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_portal.events import push_notification
from devops_portal.state import PIPELINE_STATUS


router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


def get_system_gitlab_client() -> GitLabClient:
    """获取使用系统级令牌的 GitLab 客户端。"""
    return GitLabClient(url=settings.gitlab.url, token=settings.gitlab.private_token)


async def get_requirement_author(project_id: int, issue_iid: int) -> str | None:
    """获取需求发起人 ID (使用系统令牌)。"""
    db = AuthSessionLocal()
    try:
        client = get_system_gitlab_client()
        issue = client.get_project_issue(project_id, issue_iid)
        author_id = issue.get("author", {}).get("id")
        return str(author_id) if author_id else None
    except Exception as e:
        logger.error(f"Failed to get issue author: {e}")
        return None
    finally:
        db.close()


def get_project_stakeholders_helper(project_id: int) -> list[str]:
    """获取项目干系人 ID 列表 (模拟实现，后续应从 MDM 获取)。"""
    # TODO: 实现从数据库获取项目干系人的逻辑
    return []


@router.post("/gitlab")
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

            if "type::requirement" in labels:
                review_state = next((l.replace("review-state::", "") for l in labels if l.startswith("review-state::")), "draft")
                old_review_state = next((l.replace("review-state::", "") for l in old_labels if l.startswith("review-state::")), None)
                logger.info(f"Requirement Sync: #{issue_iid} - Action: {action}, Review: {old_review_state} -> {review_state}")

                if action == "update" and old_review_state and (old_review_state != review_state):
                    try:
                        author_id = await get_requirement_author(p_id, issue_iid)
                        stakeholders = get_project_stakeholders_helper(p_id)
                        notify_targets = set(stakeholders)
                        if author_id:
                            notify_targets.add(author_id)

                        if notify_targets:
                            asyncio.create_task(
                                push_notification(
                                    list(notify_targets),
                                    f"📢 需求评审状态更新: #{issue_iid} 已流转至 [{review_state}]",
                                    "info",
                                    metadata={
                                        "project_id": p_id,
                                        "issue_iid": issue_iid,
                                        "event_type": "requirement_review_sync",
                                        "new_state": review_state,
                                        "previous_state": old_review_state,
                                    },
                                )
                            )
                    except Exception as e:
                        logger.error(f"Failed to send review notification: {e}")

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
                    "user_name": payload.get("user_name"),
                }
                logger.info(f"Pipeline Sync: Project {p_id} is now {obj.get('status')}")

                if obj.get("status") == "failed":
                    # 通用通知逻辑在此实现
                    pass

        return {"status": "accepted"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

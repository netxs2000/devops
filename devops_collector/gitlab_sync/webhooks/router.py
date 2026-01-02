"""TODO: Add module description."""
from fastapi import APIRouter, Header, Request, Depends, HTTPException
from sqlalchemy.orm import Session
import logging
from devops_collector.auth.database import get_db
from devops_collector.gitlab_sync.services.sync_service import GitLabSyncService
logger = logging.getLogger(__name__)
router = APIRouter(prefix='/webhooks/gitlab', tags=['Webhooks'])

@router.post('/events')
async def handle_gitlab_webhook(request: Request, x_gitlab_event: str=Header(None), x_gitlab_token: str=Header(None), db: Session=Depends(get_db)):
    """GitLab Webhook 统一入口
    
    实时处理来自 GitLab 的 Issue、Note、Project 等事件，保持本地镜像表数据的强一致性。
    """
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f'Failed to parse webhook JSON: {e}')
        raise HTTPException(status_code=400, detail='Invalid JSON')
    object_kind = data.get('object_kind')
    logger.info(f'Received GitLab webhook event: {object_kind}')
    sync_service = GitLabSyncService()
    if object_kind == 'issue':
        project_id = data.get('project', {}).get('id')
        issue_attributes = data.get('object_attributes', {})
        if not project_id or not issue_attributes:
            return {'status': 'error', 'message': 'Missing project or issue data'}
        try:
            sync_service.sync_issue(db, issue_attributes, project_id)
            logger.info(f"Successfully synced issue {issue_attributes.get('iid')} for project {project_id}")
            return {'status': 'success', 'event': 'issue_synced'}
        except Exception as e:
            logger.error(f'Error syncing issue via webhook: {e}')
            return {'status': 'error', 'message': str(e)}
    elif object_kind == 'note':
        note_data = data.get('object_attributes', {})
        if note_data.get('noteable_type') == 'Issue':
            project_id = data.get('project', {}).get('id')
            issue_iid = data.get('issue', {}).get('iid')
            try:
                issue_obj = sync_service.gl.projects.get(project_id).issues.get(issue_iid)
                sync_service.sync_issue(db, issue_obj.attributes, project_id)
                return {'status': 'success', 'event': 'issue_updated_by_note'}
            except Exception as e:
                logger.error(f'Error updating issue via note webhook: {e}')
                return {'status': 'error', 'message': str(e)}
    elif object_kind == 'project_destroy':
        pass
    return {'status': 'ignored', 'event': object_kind}
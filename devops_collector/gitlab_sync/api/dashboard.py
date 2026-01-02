"""TODO: Add module description."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Any
from devops_collector.auth.database import get_db
from devops_collector.auth.services import get_current_active_user
from devops_collector.models.base_models import User
from devops_collector.gitlab_sync.models.issue_metadata import IssueMetadata
from devops_collector.gitlab_sync.services.security import IssueSecurityProvider
router = APIRouter(prefix='/dashboard', tags=['Dashboard'])

@router.get('/summary')
def get_issue_summary(db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)) -> Dict[str, Any]:
    """获取仪表盘概览统计数据
    
    返回当前用户可见范围内的：
    1. 总数、打开数、关闭数。
    2. 按类型分布 (bug, requirement, task)。
    3. 按优先级分布 (P0, P1, P2)。
    """
    base_query = db.query(IssueMetadata)
    secure_query = IssueSecurityProvider.apply_issue_privacy_filter(db, base_query, current_user)
    stats = db.query(IssueMetadata.state, func.count(IssueMetadata.id)).filter(IssueMetadata.id.in_(secure_query.with_entities(IssueMetadata.id))).group_by(IssueMetadata.state).all()
    status_map = {s: count for s, count in stats}
    type_stats = db.query(IssueMetadata.issue_type, func.count(IssueMetadata.id)).filter(IssueMetadata.id.in_(secure_query.with_entities(IssueMetadata.id))).group_by(IssueMetadata.issue_type).all()
    priority_stats = db.query(IssueMetadata.priority, func.count(IssueMetadata.id)).filter(IssueMetadata.id.in_(secure_query.with_entities(IssueMetadata.id))).group_by(IssueMetadata.priority).all()
    return {'summary': {'total': sum(status_map.values()), 'opened': status_map.get('opened', 0), 'closed': status_map.get('closed', 0)}, 'by_type': {t: count for t, count in type_stats if t}, 'by_priority': {p: count for p, count in priority_stats if p}}

@router.get('/recent-issues')
def get_recent_issues(limit: int=5, db: Session=Depends(get_db), current_user: User=Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    """获取最近更新的 5 条工单详情
    
    用于仪表盘展示最新动态。
    """
    base_query = db.query(IssueMetadata)
    secure_query = IssueSecurityProvider.apply_issue_privacy_filter(db, base_query, current_user)
    recent_issues = secure_query.order_by(IssueMetadata.gitlab_updated_at.desc()).limit(limit).all()
    return [{'gitlab_project_id': issue.gitlab_project_id, 'iid': issue.gitlab_issue_iid, 'title': issue.title, 'state': issue.state, 'dept_name': issue.dept_name, 'updated_at': issue.gitlab_updated_at.isoformat() if issue.gitlab_updated_at else None} for issue in recent_issues]
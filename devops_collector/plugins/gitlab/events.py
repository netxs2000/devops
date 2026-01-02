"""GitLab 插件事件监听器模块。

实现自动化逻辑，如在产生新数据时自动更新项目的最后活跃时间。
"""
from sqlalchemy import event, func
from .models import Commit, Issue, MergeRequest, Pipeline, Note, Project

def _update_project_activity(mapper, connection, target):
    """更新关联项目的最后活跃时间辅助函数。"""
    project_id = getattr(target, 'project_id', None)
    if project_id:
        activity_time = getattr(target, 'created_at', None) or getattr(target, 'authored_date', None) or func.now()
        connection.execute(Project.__table__.update().where(Project.__table__.c.id == project_id).values(last_activity_at=activity_time))

def _handle_issue_first_response(mapper, connection, target):
    """当产生新评论时，如果评论对象是 Issue 且尚未有响应时间，则记录响应。"""
    if target.noteable_type == 'Issue':
        if getattr(target, 'system', False):
            return
        connection.execute(Issue.__table__.update().where((Issue.__table__.c.iid == target.noteable_iid) & (Issue.__table__.c.project_id == target.project_id) & (Issue.__table__.c.first_response_at == None) & (Issue.__table__.c.author_id != target.author_id)).values(first_response_at=target.created_at or func.now()))
event.listen(Commit, 'after_insert', _update_project_activity)
event.listen(Issue, 'after_insert', _update_project_activity)
event.listen(MergeRequest, 'after_insert', _update_project_activity)
event.listen(Pipeline, 'after_insert', _update_project_activity)
event.listen(Note, 'after_insert', _update_project_activity)
event.listen(Note, 'after_insert', _handle_issue_first_response)
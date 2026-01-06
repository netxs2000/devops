"""GitLab 插件事件监听器模块。

实现自动化逻辑，如在产生新数据时自动更新项目的最后活跃时间。
"""
from sqlalchemy import event, func

def _update_project_activity(mapper, connection, target):
    """更新关联项目的最后活跃时间辅助函数。"""
    from .models import GitLabProject
    project_id = getattr(target, 'project_id', None)
    if project_id:
        activity_time = (
            getattr(target, 'created_at', None) or 
            getattr(target, 'authored_date', None) or 
            func.now()
        )
        connection.execute(
            GitLabProject.__table__.update()
            .where(GitLabProject.__table__.c.id == project_id)
            .values(last_activity_at=activity_time)
        )

def _handle_issue_first_response(mapper, connection, target):
    """当产生新评论时，如果评论对象是 Issue 且尚未有响应时间，则记录响应。"""
    from .models import GitLabIssue
    if target.noteable_type == 'Issue':
        if getattr(target, 'system', False):
            return
        connection.execute(
            GitLabIssue.__table__.update()
            .where(
                (GitLabIssue.__table__.c.iid == target.noteable_iid) & 
                (GitLabIssue.__table__.c.project_id == target.project_id) & 
                (GitLabIssue.__table__.c.first_response_at == None) & 
                (GitLabIssue.__table__.c.author_id != target.author_id)
            )
            .values(first_response_at=target.created_at or func.now())
        )

def register_events():
    """注册 GitLab 模型事件。"""
    from .models import GitLabCommit, GitLabIssue, GitLabMergeRequest, GitLabPipeline, GitLabNote
    
    event.listen(GitLabCommit, 'after_insert', _update_project_activity)
    event.listen(GitLabIssue, 'after_insert', _update_project_activity)
    event.listen(GitLabMergeRequest, 'after_insert', _update_project_activity)
    event.listen(GitLabPipeline, 'after_insert', _update_project_activity)
    event.listen(GitLabNote, 'after_insert', _update_project_activity)
    event.listen(GitLabNote, 'after_insert', _handle_issue_first_response)

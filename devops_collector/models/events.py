"""全局身份映射事件监听器。

实现“一次映射，全量归责”：当由于新建立身份映射关系时，
自动追溯并关联历史存量数据（如 Commit, Issue 等）。
"""
from sqlalchemy import event, or_, func, Integer
from devops_collector.models.base_models import IdentityMapping, User

def auto_link_user_activities(mapper, connection, target):
    """当新增身份映射时，自动关联该用户在各插件中的历史活动记录。"""
    # Local import to avoid circular dependency
    from devops_collector.plugins.gitlab.models import Commit, Issue
    
    if target.source_system == 'gitlab':
        user = connection.execute(User.__table__.select().where(User.__table__.c.global_user_id == target.global_user_id)).first()
        if not user:
            return
        connection.execute(Commit.__table__.update().where((Commit.__table__.c.gitlab_user_id == None) & ((Commit.__table__.c.author_email == user.primary_email) | (Commit.__table__.c.author_name == target.external_username))).values(gitlab_user_id=target.global_user_id))
        if target.external_user_id and str(target.external_user_id).isdigit():
            gitlab_uid = int(target.external_user_id)
            connection.execute(Issue.__table__.update().where((Issue.__table__.c.author_id == None) & (func.json_extract(Issue.__table__.c.raw_data, '$.author.id').cast(Integer) == gitlab_uid)).values(author_id=target.global_user_id))
event.listen(IdentityMapping, 'after_insert', auto_link_user_activities)
"""GitLab 敏捷/迭代管理核心业务服务层。

该模块封装了“迭代管理模块”的所有核心业务逻辑，包括：
1. 看板查询 (Backlog vs Sprint)
2. 迭代规划 (Add/Remove Issues)
3. 自动化发布 (Release Automation)

这些方法设计用于被前端 API 直接调用。
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.plugins.gitlab.models import GitLabProject, GitLabIssue, GitLabMilestone, GitLabRelease, ReleaseMilestoneLink
from devops_collector.models.base_models import User
logger = logging.getLogger(__name__)

class GitLabAgileService:
    '''"""TODO: Add class description."""'''

    def __init__(self, session: Session, client: GitLabClient):
        '''"""TODO: Add description.

Args:
    self: TODO
    session: TODO
    client: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.session = session
        self.client = client

    def get_backlog_issues(self, project_id: int) -> List[GitLabIssue]:
        """获取待办需求池 (Product Backlog)。
        
        逻辑定义:
        - 归属该项目
        - 未分配里程碑 (milestone_id is NULL)
        - 状态为开启 (state = opened)
        - 类型为需求 (type::requirements) 或 Bug (type::bug)
        """
        query = self.session.query(GitLabIssue).filter(GitLabIssue.project_id == project_id, GitLabIssue.state == 'opened')
        all_issues = query.all()
        backlog = []
        for issue in all_issues:
            if issue.raw_data and issue.raw_data.get('milestone') is not None:
                continue
            labels = issue.labels or []
            if 'type::requirements' in labels or 'type::bug' in labels:
                backlog.append(issue)
        backlog.sort(key=lambda x: (x.weight or 0, x.created_at), reverse=True)
        return backlog

    def get_sprint_backlog(self, project_id: int, milestone_title: str) -> List[GitLabIssue]:
        """获取当前迭代/里程碑的需求 (Sprint Backlog)。
        
        修改说明:
        - 移除 state='opened' 过滤，返回该 Milestone 下所有状态的任务 (Opened + Closed)。
        - 前端需要利用此全量数据来计算进度条 (e.g. 8/10 Done)。
        """
        query = self.session.query(GitLabIssue).filter(GitLabIssue.project_id == project_id)
        issues = []
        for issue in query.all():
            ms = issue.raw_data.get('milestone')
            if ms and ms.get('title') == milestone_title:
                issues.append(issue)
        return issues

    def move_issue_to_sprint(self, project_id: int, issue_iid: int, milestone_id: int) -> bool:
        """【迭代规划】将 GitLabIssue 拖入迭代 (分配里程碑)。"""
        try:
            self.client.update_issue(project_id, issue_iid, {'milestone_id': milestone_id})
            return True
        except Exception as e:
            logger.error(f'Failed to move issue {issue_iid} to milestone {milestone_id}: {e}')
            return False

    def remove_issue_from_sprint(self, project_id: int, issue_iid: int) -> bool:
        """【迭代规划】将 GitLabIssue 移出迭代 (放入 Backlog)。"""
        try:
            self.client.update_issue(project_id, issue_iid, {'milestone_id': 0})
            return True
        except Exception as e:
            logger.error(f'Failed to remove issue {issue_iid} from sprint: {e}')
            return False

    def execute_release(self, project_id: int, milestone_title: str, ref_branch: str='main', user_id: Optional[str]=None, auto_rollover: bool=False, target_milestone_id: Optional[int]=None) -> Dict:
        """【核心功能】一键执行发布。 (Refactored)"""
        milestone = self.session.query(GitLabMilestone).filter(GitLabMilestone.project_id == project_id, GitLabMilestone.title == milestone_title).first()
        if not milestone:
            raise ValueError(f"GitLabMilestone '{milestone_title}' not found.")
        open_issues = []
        all_issues = self.session.query(GitLabIssue).filter(GitLabIssue.project_id == project_id, GitLabIssue.state == 'opened').all()
        for issue in all_issues:
            ms = issue.raw_data.get('milestone')
            if ms and ms.get('title') == milestone_title:
                open_issues.append(issue)
        if len(open_issues) > 0:
            if auto_rollover:
                target_ms_id = target_milestone_id or 0
                logger.info(f'Auto-rollover triggered: Moving {len(open_issues)} issues to milestone_id={target_ms_id}')
                for issue in open_issues:
                    try:
                        self.client.update_issue(project_id, issue.iid, {'milestone_id': target_ms_id})
                    except Exception as e:
                        logger.error(f'Failed to rollover issue {issue.iid}: {e}')
                        raise ValueError(f'ROLLOVER_FAILED: 无法结转任务 #{issue.iid}，发布中止。')
            else:
                issue_titles = ', '.join([f'#{i.iid} {i.title}' for i in open_issues[:3]])
                if len(open_issues) > 3:
                    issue_titles += '...'
                raise ValueError(f'CHECK_FAILED: 检测到 {len(open_issues)} 个未完成任务 ({issue_titles})。请选择“自动结转”或手动处理。')
        sprint_issues = self.get_sprint_issues_inclusive(project_id, milestone_title)
        notes = f'## 🚀 Release {milestone_title}\n\n### 变更日志\n'
        for i in sprint_issues:
            icon = '🐛' if 'type::bug' in (i.labels or []) else '✨'
            notes += f'- {icon} {i.title} (#{i.iid})\n'
        tag_name = milestone_title
        try:
            logger.info(f'Creating tag {tag_name} on branch {ref_branch}...')
            try:
                self.client.create_project_tag(project_id, tag_name, ref_branch, message=f'Release {tag_name}')
            except Exception as e:
                logger.warning(f'Tag creation failed (might exist): {e}')
            logger.info(f'Creating release {tag_name}...')
            gl_release_data = self.client.create_project_release(project_id, tag_name, description=notes, milestones=[milestone_title])
            logger.info(f'Closing milestone {milestone_title}...')
            self.client.update_project_milestone(project_id, milestone.id, {'state_event': 'close'})
            local_release = GitLabRelease(project_id=project_id, tag_name=tag_name, name=gl_release_data.get('name'), description=gl_release_data.get('description'), created_at=datetime.now(timezone.utc), released_at=datetime.now(timezone.utc), author_id=user_id, raw_data=gl_release_data)
            self.session.add(local_release)
            self.session.flush()
            local_release.milestones.append(milestone)
            self.session.commit()
            return {'status': 'success', 'tag': tag_name, 'release_notes': notes}
        except Exception as e:
            self.session.rollback()
            logger.error(f'Release execution failed: {e}')
            raise e

    def create_sprint(self, project_id: int, title: str, start_date: str, due_date: str, description: str=None) -> Dict:
        """【迭代规划】创建新的冲刺 (GitLabMilestone)。"""
        try:
            gl_milestone = self.client.create_project_milestone(project_id, title, start_date, due_date, description)
            new_ms = GitLabMilestone(id=gl_milestone['id'], iid=gl_milestone['iid'], project_id=project_id, title=gl_milestone['title'], state=gl_milestone['state'], start_date=datetime.strptime(gl_milestone['start_date'], '%Y-%m-%d') if gl_milestone.get('start_date') else None, due_date=datetime.strptime(gl_milestone['due_date'], '%Y-%m-%d') if gl_milestone.get('due_date') else None, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc), raw_data=gl_milestone)
            self.session.merge(new_ms)
            self.session.commit()
            return gl_milestone
        except Exception as e:
            logger.error(f'Failed to create sprint: {e}')
            raise e

    def get_sprint_issues_inclusive(self, project_id: int, milestone_title: str) -> List[GitLabIssue]:
        """(辅助) 获取里程碑下的所有 GitLabIssue (含已完成)。"""
        query = self.session.query(GitLabIssue).filter(GitLabIssue.project_id == project_id)
        issues = []
        for issue in query.all():
            ms = issue.raw_data.get('milestone')
            if ms and ms.get('title') == milestone_title:
                issues.append(issue)
        return issues
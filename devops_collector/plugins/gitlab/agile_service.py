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
from devops_collector.plugins.gitlab.models import (
    Project, Issue, Milestone, GitLabRelease, ReleaseMilestoneLink
)
from devops_collector.models.base_models import User

logger = logging.getLogger(__name__)

class GitLabAgileService:
    def __init__(self, session: Session, client: GitLabClient):
        self.session = session
        self.client = client

    def get_backlog_issues(self, project_id: int) -> List[Issue]:
        """获取待办需求池 (Product Backlog)。
        
        逻辑定义:
        - 归属该项目
        - 未分配里程碑 (milestone_id is NULL)
        - 状态为开启 (state = opened)
        - 类型为需求 (type::requirements) 或 Bug (type::bug)
        """
        # 注意: Label 存储为 JSON，这里使用 PostgreSQL 的 JSONB 查询语法需根据实际 DB 调整
        # SQLAlchemy 对于 JSON 字段查询通常依赖于方言，这里使用 Python 层面过滤作为通用兜底
        # 如果数据量大，强烈建议利用数据库原生 JSON 查询能力优化
        
        query = self.session.query(Issue).filter(
            Issue.project_id == project_id,
            Issue.state == 'opened',
            # Issue.milestone_id == None # 注意: Issue 模型目前可能没有直接存储 milestone_id 外键，而是存储在原始数据
            # 如果模型中没有抽取 milestone_id 字段，我们需要依赖 client 实时查询或者增强模型
            # 假设我们在模型加载时没有抽取 milestone_id (目前看 issue_mixin.py 确实没抽取)，
            # 这是一个优化的点。现在的实现我们先查所有 opened issue 然后过滤。
        )
        
        all_issues = query.all()
        
        backlog = []
        for issue in all_issues:
            # 1. 过滤掉已分配里程碑的 (从 raw_data 或关联中判断)
            # 由于 Issue 模型未显式映射 milestone_id，检查 raw_data
            if issue.raw_data and issue.raw_data.get('milestone') is not None:
                continue
                
            # 2. 过滤类型 (Requirements OR Bug)
            labels = issue.labels or []
            if 'type::requirements' in labels or 'type::bug' in labels:
                backlog.append(issue)
                
        # 排序: 权重高的在前，同权重按创建时间
        backlog.sort(key=lambda x: (x.weight or 0, x.created_at), reverse=True)
        return backlog

    def get_sprint_backlog(self, project_id: int, milestone_title: str) -> List[Issue]:
        """获取当前迭代/里程碑的需求 (Sprint Backlog)。
        
        修改说明:
        - 移除 state='opened' 过滤，返回该 Milestone 下所有状态的任务 (Opened + Closed)。
        - 前端需要利用此全量数据来计算进度条 (e.g. 8/10 Done)。
        """
        query = self.session.query(Issue).filter(
            Issue.project_id == project_id
        )
        
        issues = []
        for issue in query.all():
            ms = issue.raw_data.get('milestone')
            if ms and ms.get('title') == milestone_title:
                issues.append(issue)
                
        return issues

    def move_issue_to_sprint(self, project_id: int, issue_iid: int, milestone_id: int) -> bool:
        """【迭代规划】将 Issue 拖入迭代 (分配里程碑)。"""
        try:
            # 1. 调用 GitLab API 更新
            self.client.update_issue(project_id, issue_iid, {'milestone_id': milestone_id})
            
            # 2. (可选) 同步更新本地数据库状态以免需重新全量同步
            #    但为了数据一致性，通常建议触发一次该 Issue 的单条同步
            return True
        except Exception as e:
            logger.error(f"Failed to move issue {issue_iid} to milestone {milestone_id}: {e}")
            return False

    def remove_issue_from_sprint(self, project_id: int, issue_iid: int) -> bool:
        """【迭代规划】将 Issue 移出迭代 (放入 Backlog)。"""
        try:
            # milestone_id=0 或 null 在某些版本 API 中表示移除，通常设为 0
            # GitLab API 文档: milestone_id (optional) - The global ID of a milestone to assign issue. Set to 0 or unassign to remove milestone.
            self.client.update_issue(project_id, issue_iid, {'milestone_id': 0})
            return True
        except Exception as e:
            logger.error(f"Failed to remove issue {issue_iid} from sprint: {e}")
            return False

    def execute_release(self, project_id: int, milestone_title: str, 
                       ref_branch: str = 'main', 
                       user_id: Optional[str] = None,
                       auto_rollover: bool = False,
                       target_milestone_id: Optional[int] = None) -> Dict:
        """【核心功能】一键执行发布。 (Refactored)"""
        # 1. 查找里程碑
        milestone = self.session.query(Milestone).filter(
            Milestone.project_id == project_id,
            Milestone.title == milestone_title
        ).first()

        if not milestone:
            raise ValueError(f"Milestone '{milestone_title}' not found.")
            
        # 2. [增强] 检查未完成任务 (Pre-flight Check & Rollover)
        open_issues = []
        all_issues = self.session.query(Issue).filter(
            Issue.project_id == project_id,
            Issue.state == 'opened'
        ).all()
        
        for issue in all_issues:
            ms = issue.raw_data.get('milestone')
            if ms and ms.get('title') == milestone_title:
                open_issues.append(issue)
                
        if len(open_issues) > 0:
            if auto_rollover:
                # 执行自动结转
                target_ms_id = target_milestone_id or 0 # 0 表示移出 Milestone (Backlog)
                logger.info(f"Auto-rollover triggered: Moving {len(open_issues)} issues to milestone_id={target_ms_id}")
                
                for issue in open_issues:
                    try:
                        self.client.update_issue(project_id, issue.iid, {'milestone_id': target_ms_id})
                    except Exception as e:
                        logger.error(f"Failed to rollover issue {issue.iid}: {e}")
                        # 这是一个部分失败的情况，最好抛出异常中止发布，避免状态不一致
                        raise ValueError(f"ROLLOVER_FAILED: 无法结转任务 #{issue.iid}，发布中止。")
                
                # 结转成功后，视为当前迭代已清空，继续流程
            else:
                # 抛出特定格式错误，供前端识别并弹窗
                # 格式: CHECK_FAILED|{count}|{issue_sample}
                issue_titles = ", ".join([f"#{i.iid} {i.title}" for i in open_issues[:3]])
                if len(open_issues) > 3:
                    issue_titles += "..."
                raise ValueError(f"CHECK_FAILED: 检测到 {len(open_issues)} 个未完成任务 ({issue_titles})。请选择“自动结转”或手动处理。")

        # 3. 生成 Release Notes
        sprint_issues = self.get_sprint_issues_inclusive(project_id, milestone_title)
        notes = f"## 🚀 Release {milestone_title}\n\n### 变更日志\n"
        for i in sprint_issues:
            icon = "🐛" if "type::bug" in (i.labels or []) else "✨"
            notes += f"- {icon} {i.title} (#{i.iid})\n"
            
        # 4. 执行发布
        tag_name = milestone_title
        try:
            # A. Tag
            logger.info(f"Creating tag {tag_name} on branch {ref_branch}...")
            try:
                self.client.create_project_tag(project_id, tag_name, ref_branch, message=f"Release {tag_name}")
            except Exception as e:
                logger.warning(f"Tag creation failed (might exist): {e}")
            
            # B. Release
            logger.info(f"Creating release {tag_name}...")
            gl_release_data = self.client.create_project_release(
                project_id, tag_name, description=notes, milestones=[milestone_title]
            )
            
            # C. Close Milestone
            logger.info(f"Closing milestone {milestone_title}...")
            self.client.update_project_milestone(project_id, milestone.id, {'state_event': 'close'})
            
            # 5. Local Save
            local_release = GitLabRelease(
                project_id=project_id, tag_name=tag_name, name=gl_release_data.get('name'),
                description=gl_release_data.get('description'),
                created_at=datetime.now(timezone.utc), released_at=datetime.now(timezone.utc),
                author_id=user_id, raw_data=gl_release_data
            )
            self.session.add(local_release)
            self.session.flush()
            local_release.milestones.append(milestone)
            self.session.commit()
            
            return {"status": "success", "tag": tag_name, "release_notes": notes}
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Release execution failed: {e}")
            raise e

    def create_sprint(self, project_id: int, title: str, start_date: str, due_date: str, description: str = None) -> Dict:
        """【迭代规划】创建新的冲刺 (Milestone)。"""
        try:
            gl_milestone = self.client.create_project_milestone(
                project_id, title, start_date, due_date, description
            )
            
            new_ms = Milestone(
                id=gl_milestone['id'], iid=gl_milestone['iid'], project_id=project_id,
                title=gl_milestone['title'], state=gl_milestone['state'],
                start_date=datetime.strptime(gl_milestone['start_date'], '%Y-%m-%d') if gl_milestone.get('start_date') else None,
                due_date=datetime.strptime(gl_milestone['due_date'], '%Y-%m-%d') if gl_milestone.get('due_date') else None,
                created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
                raw_data=gl_milestone
            )
            self.session.merge(new_ms)
            self.session.commit()
            return gl_milestone
        except Exception as e:
            logger.error(f"Failed to create sprint: {e}")
            raise e

    def get_sprint_issues_inclusive(self, project_id: int, milestone_title: str) -> List[Issue]:
        """(辅助) 获取里程碑下的所有 Issue (含已完成)。"""
        query = self.session.query(Issue).filter(Issue.project_id == project_id)
        issues = []
        for issue in query.all():
            ms = issue.raw_data.get('milestone')
            if ms and ms.get('title') == milestone_title:
                issues.append(issue)
        return issues

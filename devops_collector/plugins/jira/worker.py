"""Jira 数据采集 Worker"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from devops_collector.models.base_models import Organization, User as GlobalUser, TraceabilityLink

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from .client import JiraClient
from .models import JiraProject, JiraBoard, JiraSprint, JiraIssue, JiraIssueHistory
from devops_collector.core.identity_manager import IdentityManager

logger = logging.getLogger(__name__)

class JiraWorker(BaseWorker):
    """Jira 数据采集 Worker。"""
    SCHEMA_VERSION = "1.0"
    
    def __init__(self, session: Session, client: JiraClient):
        super().__init__(session, client)

    def process_task(self, task: dict) -> None:
        """处理 Jira 同步任务。"""
        project_key = task.get('project_key')
        logger.info(f"Processing Jira task: project_key={project_key}")
        
        try:
            # 0. 同步组织架构 (Groups) 与全量人员
            self._sync_groups()
            self._sync_all_users()

            # 1. 同步项目信息
            project = self._sync_project(project_key)
            if not project:
                return

            # 2. 同步看板
            boards = self.client.get_boards(project_key)
            for b_data in boards:
                board = self._sync_board(project, b_data)
                
                # 3. 同步 Sprint
                if board.type == 'scrum':
                    sprints = self.client.get_sprints(board.id)
                    for s_data in sprints:
                        self._sync_sprint(board, s_data)

            # 4. 同步 Issues
            jql = f"project = '{project_key}'"
            if project.last_synced_at:
                jql += f" AND updated >= '{project.last_synced_at.strftime('%Y-%m-%d %H:%M')}'"
            
            issues = self.client.get_issues(jql)
            for i_data in issues:
                self._sync_issue(project, i_data)

            project.last_synced_at = datetime.now(timezone.utc)
            project.sync_status = 'COMPLETED'
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to sync Jira project {project_key}: {e}")
            raise

    def _sync_project(self, project_key: str) -> Optional[JiraProject]:
        """同步项目元数据。"""
        # 简化版：Jira API 获取单个项目可能需要额外调用，这里假设已经知道 Key
        # 实际实现中可以通过 get_projects 过滤
        project = self.session.query(JiraProject).filter_by(key=project_key).first()
        if not project:
            # 尝试从 API 获取详情 (此处示例逻辑)
            response = self.client._get(f"/rest/api/3/project/{project_key}")
            p_data = response.json()
            # 原始项目数据落盘
            self.save_to_staging(
                source='jira',
                entity_type='project',
                external_id=project_key,
                payload=p_data,
                schema_version=self.SCHEMA_VERSION
            )
            project = JiraProject(
                key=p_data['key'],
                name=p_data['name'],
                description=p_data.get('description'),
                lead_name=p_data.get('lead', {}).get('displayName'),
                raw_data=p_data
            )
            self.session.add(project)
            self.session.flush()
        return project

    def _sync_board(self, project: JiraProject, data: dict) -> JiraBoard:
        board = self.session.query(JiraBoard).filter_by(id=data['id']).first()
        if not board:
            board = JiraBoard(id=data['id'], project_id=project.id)
            self.session.add(board)
        
        # 原始看板数据落盘
        self.save_to_staging(
            source='jira',
            entity_type='board',
            external_id=data['id'],
            payload=data,
            schema_version=self.SCHEMA_VERSION
        )
        
        board.name = data['name']
        board.type = data['type']
        board.raw_data = data
        self.session.flush()
        return board

    def _sync_sprint(self, board: JiraBoard, data: dict) -> JiraSprint:
        sprint = self.session.query(JiraSprint).filter_by(id=data['id']).first()
        if not sprint:
            sprint = JiraSprint(id=data['id'], board_id=board.id)
            self.session.add(sprint)
        
        # 原始 Sprint 数据落盘
        self.save_to_staging(
            source='jira',
            entity_type='sprint',
            external_id=data['id'],
            payload=data,
            schema_version=self.SCHEMA_VERSION
        )
        
        sprint.name = data['name']
        sprint.state = data['state']
        
        if data.get('startDate'):
            sprint.start_date = datetime.fromisoformat(data['startDate'].replace('Z', '+00:00'))
        if data.get('endDate'):
            sprint.end_date = datetime.fromisoformat(data['endDate'].replace('Z', '+00:00'))
        if data.get('completeDate'):
            sprint.complete_date = datetime.fromisoformat(data['completeDate'].replace('Z', '+00:00'))
            
        sprint.raw_data = data
        self.session.flush()
        return sprint

    def _sync_issue(self, project: JiraProject, data: dict) -> JiraIssue:
        """同步 Jira 问题：先落盘到 Staging，再执行业务转换。"""
        # 1. Extract & Load (Staging)
        self.save_to_staging(
            source='jira',
            entity_type='issue',
            external_id=data['id'],
            payload=data,
            schema_version=self.SCHEMA_VERSION
        )
        
        # 2. Transform & Load (DW)
        return self._transform_issue(project, data)

    def _transform_issue(self, project: JiraProject, data: dict) -> JiraIssue:
        """核心解析逻辑：将原始 Jira JSON 转换为 JiraIssue 模型。"""
        issue = self.session.query(JiraIssue).filter_by(id=data['id']).first()
        if not issue:
            issue = JiraIssue(id=data['id'], key=data['key'], project_id=project.id)
            self.session.add(issue)
        
        fields = data.get('fields', {})
        issue.summary = fields.get('summary')
        issue.description = fields.get('description')
        issue.status = fields.get('status', {}).get('name')
        issue.priority = fields.get('priority', {}).get('name')
        issue.issue_type = fields.get('issuetype', {}).get('name')
        
        # 映射内部用户
        if fields.get('assignee'):
            u = IdentityManager.get_or_create_user(
                self.session, 'jira', fields['assignee']['accountId'], 
                fields['assignee'].get('emailAddress'), fields['assignee'].get('displayName')
            )
            issue.assignee_user_id = u.id
            issue.assignee_name = u.name
            
        if fields.get('reporter'):
            u = IdentityManager.get_or_create_user(
                self.session, 'jira', fields['reporter']['accountId'], 
                fields['reporter'].get('emailAddress'), fields['reporter'].get('displayName')
            )
            issue.reporter_user_id = u.id
            issue.reporter_name = u.name
            
        if fields.get('creator'):
            u = IdentityManager.get_or_create_user(
                self.session, 'jira', fields['creator']['accountId'], 
                fields['creator'].get('emailAddress'), fields['creator'].get('displayName')
            )
            issue.creator_user_id = u.id
            issue.creator_name = u.name
        
        if fields.get('created'):
            issue.created_at = datetime.fromisoformat(fields['created'].replace('Z', '+00:00'))
        if fields.get('updated'):
            issue.updated_at = datetime.fromisoformat(fields['updated'].replace('Z', '+00:00'))
        if fields.get('resolutiondate'):
            issue.resolved_at = datetime.fromisoformat(fields['resolutiondate'].replace('Z', '+00:00'))
            
        # 解析扩展字段
        issue.original_estimate = fields.get('timeoriginalestimate')
        issue.time_spent = fields.get('timespent')
        issue.remaining_estimate = fields.get('timeestimate')
        issue.labels = fields.get('labels', [])
        
        # 解析版本 (里程碑)
        if fields.get('fixVersions'):
            issue.fix_versions = [v.get('name') for v in fields['fixVersions']]
            
        issue.raw_data = data
        self.session.flush()
        
        # 同步变更历史
        if 'changelog' in data:
            self._sync_issue_history(issue, data['changelog'])
            
        # 同步 Issue Links (依赖分析)
        if fields.get('issuelinks'):
            self._sync_issue_links(issue, fields['issuelinks'])
            
        return issue

    def _sync_issue_history(self, issue: JiraIssue, changelog: dict) -> None:
        """同步 Jira 问题的变更历史。"""
        for history in changelog.get('histories', []):
            author = history.get('author', {}).get('displayName')
            created = datetime.fromisoformat(history['created'].replace('Z', '+00:00'))
            
            for item in history.get('items', []):
                # 我们主要关注状态变更，但模型可以存储通用变更
                history_id = f"{history['id']}_{item.get('field')}"
                h_record = self.session.query(JiraIssueHistory).filter_by(id=history_id).first()
                if not h_record:
                    h_record = JiraIssueHistory(
                        id=history_id,
                        issue_id=issue.id,
                        author_name=author,
                        created_at=created,
                        field=item.get('field'),
                        from_string=item.get('fromString'),
                        to_string=item.get('toString'),
                        raw_data=history
                    )
                    self.session.add(h_record)
        self.session.flush()

    def _sync_issue_links(self, issue: JiraIssue, links: List[Dict[str, Any]]) -> None:
        """同步 Jira 问题的链路关系 (依赖分析)。
        
        Args:
            issue: JiraIssue 对象
            links: Jira API 返回的 issuelinks 列表
        """
        for link in links:
            # 识别是 inward 还是 outward
            target_issue_data = None
            link_direction = None
            
            if 'outwardIssue' in link:
                target_issue_data = link['outwardIssue']
                link_direction = link.get('type', {}).get('outward')
            elif 'inwardIssue' in link:
                target_issue_data = link['inwardIssue']
                link_direction = link.get('type', {}).get('inward')
                
            if not target_issue_data or not link_direction:
                continue
                
            # 使用 TraceabilityLink 存储
            source_ext_id = str(issue.id)
            target_ext_id = str(target_issue_data['id'])
            
            # 检查是否已存在 (避免重复创建)
            existing = self.session.query(TraceabilityLink).filter_by(
                source_system='jira',
                source_id=source_ext_id,
                target_id=target_ext_id,
                link_type=link_direction
            ).first()
            
            if not existing:
                link_record = TraceabilityLink(
                    source_system='jira',
                    source_type='issue',
                    source_id=source_ext_id,
                    target_system='jira',
                    target_type='issue',
                    target_id=target_ext_id,
                    link_type=link_direction,
                    raw_data=link
                )
                self.session.add(link_record)
        
        self.session.flush()

    def _sync_groups(self) -> None:
        """同步 Jira 用户组到公共 Organization 表。"""
        groups = self.client.get_groups()
        for g in groups:
            # 可以在这里增加过滤逻辑，只同步感兴趣的组
            org = self.session.query(Organization).filter_by(name=g['name']).first()
            if not org:
                org = Organization(name=g['name'], level='Group')
                self.session.add(org)
        self.session.flush()

    def _sync_all_users(self) -> None:
        """同步 Jira 全量用户，利用 IdentityManager 进行自动对齐。"""
        users = self.client.get_all_users()
        for u_data in users:
            if u_data.get('accountType') != 'atlassian': # 过滤服务账号或虚拟账号
                continue
                
            IdentityManager.get_or_create_user(
                self.session, 
                source='jira',
                external_id=u_data['accountId'],
                email=u_data.get('emailAddress'),
                name=u_data.get('displayName')
            )
            
        self.session.flush()

PluginRegistry.register_worker('jira', JiraWorker)

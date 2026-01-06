"""GitLab Worker Issue Mixin.

提供 Issue 及其相关时间 (Event) 的同步、Staging 和 Transformation 逻辑。
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict
from devops_collector.core.utils import parse_iso8601
from devops_collector.plugins.gitlab.models import Project, Issue, GitLabIssueEvent, IssueStateTransition, Blockage #, TestCase
from devops_collector.plugins.gitlab.parser import GitLabTestParser
logger = logging.getLogger(__name__)

class IssueMixin:
    """提供 GitLab Issue 相关的同步逻辑 Mixin。

    支持对 Issue 基础元数据、状态变迁历史 (Transitions) 以及阻塞事件 (Blockages) 的同步。
    """

    def _sync_issues(self, project: Project, since: Optional[str]) -> int:
        """从项目同步 Issue。
        
        Args:
            project (Project): 关联的项目实体。
            since (Optional[str]): ISO 格式时间字符串，仅同步该时间之后的 Issue。
            
        Returns:
            int: 同步处理的 Issue 总数。
        """
        return self._process_generator(self.client.get_project_issues(project.id, since=since), lambda batch: self._save_issues_batch(project, batch))

    def _save_issues_batch(self, project: Project, batch: List[dict]) -> None:
        """批量保存来自 API 的 Issue 原始数据及其转换后的实体。

        Args:
            project (Project): 关联的 Project 模型对象。
            batch (List[dict]): 包含多个 Issue 原始 JSON 数据的列表。
        """
        for data in batch:
            self.save_to_staging(source='gitlab', entity_type='issue', external_id=data['id'], payload=data, schema_version=self.SCHEMA_VERSION)
        self._transform_issues_batch(project, batch)

    def _transform_issues_batch(self, project: Project, batch: List[dict]) -> None:
        """将原始 JSON 数据转换并加载至 Issue 实体模型中。

        支持增量更新，当 ID 冲突时会更新现有记录。

        Args:
            project (Project): 关联的 Project 模型对象。
            batch (List[dict]): 包含多个 Issue 原始 JSON 数据的列表。
        """
        ids = [item['id'] for item in batch]
        existing = self.session.query(Issue).filter(Issue.id.in_(ids)).all()
        existing_map = {i.id: i for i in existing}
        for data in batch:
            issue = existing_map.get(data['id'])
            if not issue:
                issue = Issue(id=data['id'])
                self.session.add(issue)
            issue.project_id = project.id
            issue.iid = data['iid']
            issue.title = data['title']
            issue.description = data.get('description')
            issue.state = data['state']
            issue.created_at = parse_iso8601(data['created_at'])
            issue.updated_at = parse_iso8601(data['updated_at'])
            if data.get('closed_at'):
                issue.closed_at = parse_iso8601(data['closed_at'])
            time_stats = data.get('time_stats', {})
            issue.time_estimate = time_stats.get('time_estimate')
            issue.total_time_spent = time_stats.get('total_time_spent')
            issue.labels = data.get('labels', [])
            issue.weight = data.get('weight')
            issue.work_item_type = data.get('issue_type') or 'issue'
            if data.get('author'):
                if self.user_resolver:
                    uid = self.user_resolver.resolve(data['author']['id'])
                    issue.author_id = uid
            # if 'type::test' in issue.labels:
            #     self._sync_test_case_from_issue(project, issue, data)
            if self.enable_deep_analysis and 'iid' in data and hasattr(self, 'client'):
                try:
                    self._sync_issue_events(project, data)
                    self._sync_issue_flow_details(project, data)
                except Exception as e:
                    logger.warning(f'Failed to sync details for issue {issue.iid}: {e}')

    def _sync_issue_events(self, project: Project, issue_data: Dict) -> None:
        """同步指定 Issue 的全量资源事件 (状态、标签、里程碑)。

        通过调用 GitLab 事件接口，捕捉每一个状态变迁点。

        Args:
            project (Project): 关联的 Project 对象。
            issue_data (Dict): Issue 的详情字典 (必须包含 id 和 iid)。
        """
        project_id = project.id
        issue_iid = issue_data['iid']
        issue_id = issue_data['id']
        for event in self.client.get_issue_state_events(project_id, issue_iid):
            self._save_issue_event(issue_id, 'state', event)
        for event in self.client.get_issue_label_events(project_id, issue_iid):
            self._save_issue_event(issue_id, 'label', event)
        for event in self.client.get_issue_milestone_events(project_id, issue_iid):
            self._save_issue_event(issue_id, 'milestone', event)

    def _save_issue_event(self, issue_id: int, event_type: str, data: Dict) -> None:
        """保存 Issue 事件，确保幂等性。

        用于将 GitLab 的原子事件（如状态变更、标签变更等）同步至数据库。

        Args:
            issue_id (int): 数据库中对应的 Issue 内部 ID。
            event_type (str): 事件分类 (state, label, milestone 等)。
            data (Dict): 来自 GitLab API 的原始事件元数据字典。
        """
        external_id = data['id']
        existing = self.session.query(GitLabIssueEvent).filter_by(issue_id=issue_id, event_type=event_type, external_event_id=external_id).first()
        if existing:
            return
        event = GitLabIssueEvent(issue_id=issue_id, event_type=event_type, external_event_id=external_id, action=data.get('state') or data.get('action') or 'update', created_at=parse_iso8601(data.get('created_at')), meta_info=data)
        if data.get('user') and self.user_resolver:
            event.user_id = self.user_resolver.resolve(data['user']['id'])
        self.session.add(event)

    def _sync_issue_flow_details(self, project: Project, issue_data: Dict) -> None:
        """同步 Issue 的流转历史细节与阻塞记录 (用于流动效能分析)。

        基于 GitLab 资源事件重建 Issue 的状态演进过程并识别阻塞区间。
        这些数据是计算周期时间 (Cycle Time) 和流动效率的基础。

        Args:
            project (Project): 关联的 Project 数据库模型实例。
            issue_data (Dict): 从 GitLab API 获取的原始 Issue 详情数据字典。
        """
        issue_id = issue_data['id']
        issue_iid = issue_data['iid']
        state_events = sorted(list(self.client.get_issue_state_events(project.id, issue_iid)), key=lambda x: x['created_at'])
        last_state = 'opened'
        last_time = parse_iso8601(issue_data['created_at'])
        for event in state_events:
            current_state = event['state']
            current_time = parse_iso8601(event['created_at'])
            duration = (current_time - last_time).total_seconds() / 3600.0
            existing = self.session.query(IssueStateTransition).filter_by(issue_id=issue_id, to_state=current_state, timestamp=current_time).first()
            if not existing:
                trans = IssueStateTransition(issue_id=issue_id, from_state=last_state, to_state=current_state, timestamp=current_time, duration_hours=duration)
                self.session.add(trans)
            last_state = current_state
            last_time = current_time
        label_events = sorted(list(self.client.get_issue_label_events(project.id, issue_iid)), key=lambda x: x['created_at'])
        for event in label_events:
            label_name = event.get('label', {}).get('name', '').lower()
            if 'blocked' not in label_name:
                continue
            action = event['action']
            event_time = parse_iso8601(event['created_at'])
            if action == 'add':
                existing = self.session.query(Blockage).filter_by(issue_id=issue_id, start_time=event_time).first()
                if not existing:
                    active_blockage = Blockage(issue_id=issue_id, reason=label_name, start_time=event_time)
                    self.session.add(active_blockage)
            elif action == 'remove':
                last_block = self.session.query(Blockage).filter(Blockage.issue_id == issue_id, Blockage.end_time == None).order_by(Blockage.start_time.desc()).first()
                if last_block:
                    last_block.end_time = event_time

    def _sync_test_case_from_issue(self, project: Project, issue: Issue, data: dict) -> None:
        """从 Issue 描述解析并同步测试用例。
        
        Args:
            project: 关联的项目。
            issue: 已转换的 Issue 对象。
            data: 原始 Issue 数据。
        """
        parsed = GitLabTestParser.parse_description(issue.description or '')
        test_case = self.session.query(TestCase).filter_by(project_id=project.id, iid=issue.iid).first()
        if not test_case:
            test_case = TestCase(project_id=project.id, iid=issue.iid, author_id=issue.author_id)
            self.session.add(test_case)
        test_case.title = issue.title
        test_case.priority = parsed['priority']
        test_case.test_type = parsed['test_type']
        test_case.pre_conditions = parsed['pre_conditions']
        test_case.test_steps = parsed['test_steps']
        test_case.description = issue.description
        req_iid = GitLabTestParser.extract_requirement_id(issue.description or '')
        if req_iid:
            req_issue = self.session.query(Issue).filter_by(project_id=project.id, iid=req_iid).first()
            if req_issue and req_issue not in test_case.linked_issues:
                test_case.linked_issues.append(req_issue)
                logger.debug(f'Linked TestCase !{issue.iid} to Requirement !{req_iid}')
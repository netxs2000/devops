"""禅道 (ZenTao) 全量数据采集 Worker"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from devops_collector.models.base_models import Organization, User as GlobalUser, IdentityMapping
from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from devops_collector.core.identity_manager import IdentityManager
from devops_collector.core.services import close_current_and_insert_new
from .client import ZenTaoClient
from .models import ZenTaoProduct, ZenTaoExecution, ZenTaoIssue, ZenTaoProductPlan, ZenTaoTestCase, ZenTaoTestResult, ZenTaoBuild, ZenTaoRelease, ZenTaoAction
logger = logging.getLogger(__name__)

class ZenTaoWorker(BaseWorker):
    """禅道全量数据采集 Worker。"""
    SCHEMA_VERSION = '1.0'

    def __init__(self, session: Session, client: ZenTaoClient):
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
        super().__init__(session, client)

    def process_task(self, task: dict) -> None:
        """处理禅道同步任务。"""
        product_id = task.get('product_id')
        logger.info(f'Processing ZenTao full-scale task: product_id={product_id}')
        try:
            product = self._sync_product(product_id)
            if not product:
                return
            self._sync_org_structure()
            self._sync_zentao_users()
            plans_data = self.client.get_plans(product.id)
            for p_data in plans_data:
                self._sync_plan(product.id, p_data)
            executions_data = self.client.get_executions()
            for e_data in executions_data:
                self._sync_execution(product.id, e_data)
            stories = self.client.get_stories(product.id)
            for s_data in stories:
                self._sync_issue(product.id, s_data, 'feature')
            bugs = self.client.get_bugs(product.id)
            for b_data in bugs:
                self._sync_issue(product.id, b_data, 'bug')
            test_cases = self.client.get_test_cases(product.id)
            for tc_data in test_cases:
                tc = self._sync_test_case(product.id, tc_data)
                results = self.client.get_test_results(tc.id)
                for r_data in results:
                    self._sync_test_result(tc.id, r_data)
            releases = self.client.get_releases(product.id)
            for rel_data in releases:
                self._sync_release(product.id, rel_data)
            product_executions = self.session.query(ZenTaoExecution).filter_by(product_id=product.id).all()
            for exec_item in product_executions:
                builds = self.client.get_builds(exec_item.id)
                for b_data in builds:
                    self._sync_build(product.id, exec_item.id, b_data)
            actions = self.client.get_actions(product.id)
            for a_data in actions:
                self._sync_action(product.id, a_data)
            product.last_synced_at = datetime.now(timezone.utc)
            product.sync_status = 'COMPLETED'
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f'Failed to sync ZenTao product {product_id}: {e}')
            raise

    def _sync_product(self, product_id: int) -> Optional[ZenTaoProduct]:
        '''"""TODO: Add description.

Args:
    self: TODO
    product_id: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        product = self.session.query(ZenTaoProduct).filter_by(id=product_id).first()
        if not product:
            response = self.client._get(f'/products/{product_id}')
            p_data = response.json()
            self.save_to_staging(source='zentao', entity_type='product', external_id=product_id, payload=p_data, schema_version=self.SCHEMA_VERSION)
            product = ZenTaoProduct(id=p_data['id'], name=p_data['name'], code=p_data.get('code'), description=p_data.get('description'), status=p_data.get('status'), raw_data=p_data)
            self.session.add(product)
            self.session.flush()
        return product

    def _sync_execution(self, product_id: int, data: dict) -> ZenTaoExecution:
        '''"""TODO: Add description.

Args:
    self: TODO
    product_id: TODO
    data: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        exe = self.session.query(ZenTaoExecution).filter_by(id=data['id']).first()
        if not exe:
            exe = ZenTaoExecution(id=data['id'], product_id=product_id)
            self.session.add(exe)
        self.save_to_staging(source='zentao', entity_type='execution', external_id=data['id'], payload=data, schema_version=self.SCHEMA_VERSION)
        exe.name = data.get('name')
        exe.code = data.get('code')
        exe.type = data.get('type')
        exe.status = data.get('status')
        if data.get('begin'):
            exe.begin = datetime.fromisoformat(data['begin'].replace(' ', 'T'))
        if data.get('end'):
            exe.end = datetime.fromisoformat(data['end'].replace(' ', 'T'))
        exe.raw_data = data
        self.session.flush()
        return exe

    def _sync_plan(self, product_id: int, data: dict) -> ZenTaoProductPlan:
        '''"""TODO: Add description.

Args:
    self: TODO
    product_id: TODO
    data: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        plan = self.session.query(ZenTaoProductPlan).filter_by(id=data['id']).first()
        if not plan:
            plan = ZenTaoProductPlan(id=data['id'], product_id=product_id)
            self.session.add(plan)
        self.save_to_staging(source='zentao', entity_type='plan', external_id=data['id'], payload=data, schema_version=self.SCHEMA_VERSION)
        plan.title = data.get('title')
        if data.get('begin'):
            plan.begin = datetime.fromisoformat(data['begin'].replace(' ', 'T'))
        if data.get('end'):
            plan.end = datetime.fromisoformat(data['end'].replace(' ', 'T'))
        plan.status = data.get('status')
        plan.desc = data.get('desc')
        plan.opened_by = data.get('openedBy')
        if plan.opened_by:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', plan.opened_by)
            plan.opened_by_user_id = u.global_user_id
        if data.get('openedDate'):
            plan.opened_date = datetime.fromisoformat(data['openedDate'].replace(' ', 'T'))
        plan.raw_data = data
        self.session.flush()
        return plan

    def _sync_issue(self, product_id: int, data: dict, issue_type: str) -> ZenTaoIssue:
        """同步禅道问题：先落盘到 Staging，再执行业务转换。"""
        self.save_to_staging(source='zentao', entity_type=f'issue_{issue_type}', external_id=data['id'], payload=data, schema_version=self.SCHEMA_VERSION)
        return self._transform_issue(product_id, data, issue_type)

    def _transform_issue(self, product_id: int, data: dict, issue_type: str) -> ZenTaoIssue:
        """核心解析逻辑：将原始禅道 JSON 转换为 ZenTaoIssue 模型。"""
        issue = self.session.query(ZenTaoIssue).filter_by(id=data['id'], type=issue_type).first()
        if not issue:
            issue = ZenTaoIssue(id=data['id'], product_id=product_id, type=issue_type)
            self.session.add(issue)
        issue.plan_id = data.get('plan')
        issue.title = data.get('title') or data.get('name')
        issue.status = data.get('status')
        issue.priority = data.get('priority')
        issue.opened_by = data.get('openedBy')
        if issue.opened_by:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', issue.opened_by)
            issue.opened_by_user_id = u.global_user_id
        issue.assigned_to = data.get('assignedTo')
        if issue.assigned_to:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', issue.assigned_to)
            issue.assigned_to_user_id = u.global_user_id
            issue.user_id = u.global_user_id
        if data.get('openedDate'):
            try:
                issue.created_at = datetime.fromisoformat(data['openedDate'].replace(' ', 'T'))
            except:
                pass
        if data.get('lastEditedDate'):
            try:
                issue.updated_at = datetime.fromisoformat(data['lastEditedDate'].replace(' ', 'T'))
            except:
                pass
        if data.get('closedDate'):
            try:
                issue.closed_at = datetime.fromisoformat(data['closedDate'].replace(' ', 'T'))
            except:
                pass
        issue.raw_data = data
        self.session.flush()
        return issue

    def _sync_test_case(self, product_id: int, data: dict) -> ZenTaoTestCase:
        '''"""TODO: Add description.

Args:
    self: TODO
    product_id: TODO
    data: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        tc = self.session.query(ZenTaoTestCase).filter_by(id=data['id']).first()
        if not tc:
            tc = ZenTaoTestCase(id=data['id'], product_id=product_id)
            self.session.add(tc)
        self.save_to_staging(source='zentao', entity_type='test_case', external_id=data['id'], payload=data, schema_version=self.SCHEMA_VERSION)
        tc.title = data.get('title')
        tc.type = data.get('type')
        tc.status = data.get('status')
        tc.last_run_result = data.get('lastRunResult')
        tc.opened_by = data.get('openedBy')
        if tc.opened_by:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', tc.opened_by)
            tc.opened_by_user_id = u.global_user_id
        if data.get('openedDate'):
            tc.opened_date = datetime.fromisoformat(data['openedDate'].replace(' ', 'T'))
        tc.raw_data = data
        self.session.flush()
        return tc

    def _sync_test_result(self, case_id: int, data: dict) -> ZenTaoTestResult:
        '''"""TODO: Add description.

Args:
    self: TODO
    case_id: TODO
    data: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        res = self.session.query(ZenTaoTestResult).filter_by(id=data['id']).first()
        if not res:
            res = ZenTaoTestResult(id=data['id'], case_id=case_id)
            self.session.add(res)
        res.result = data.get('caseResult')
        if data.get('date'):
            res.date = datetime.fromisoformat(data['date'].replace(' ', 'T'))
        res.last_run_by = data.get('lastRunBy')
        res.raw_data = data
        self.session.flush()
        return res

    def _sync_build(self, product_id: int, execution_id: int, data: dict) -> ZenTaoBuild:
        '''"""TODO: Add description.

Args:
    self: TODO
    product_id: TODO
    execution_id: TODO
    data: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        build = self.session.query(ZenTaoBuild).filter_by(id=data['id']).first()
        if not build:
            build = ZenTaoBuild(id=data['id'], product_id=product_id, execution_id=execution_id)
            self.session.add(build)
        self.save_to_staging(source='zentao', entity_type='build', external_id=data['id'], payload=data, schema_version=self.SCHEMA_VERSION)
        return self._transform_build(product_id, execution_id, data)

    def _transform_build(self, product_id: int, execution_id: int, data: dict) -> ZenTaoBuild:
        """从原始数据转换并加载 Build。"""
        build = self.session.query(ZenTaoBuild).filter_by(id=data['id']).first()
        if not build:
            build = ZenTaoBuild(id=data['id'], product_id=product_id, execution_id=execution_id)
            self.session.add(build)
        build.name = data.get('name')
        build.builder = data.get('builder')
        if build.builder:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', build.builder)
            build.builder_user_id = u.global_user_id
        if data.get('date'):
            build.date = datetime.fromisoformat(data['date'].replace(' ', 'T'))
        build.raw_data = data
        self.session.flush()
        return build

    def _sync_release(self, product_id: int, data: dict) -> ZenTaoRelease:
        '''"""TODO: Add description.

Args:
    self: TODO
    product_id: TODO
    data: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        rel = self.session.query(ZenTaoRelease).filter_by(id=data['id']).first()
        if not rel:
            rel = ZenTaoRelease(id=data['id'], product_id=product_id)
            self.session.add(rel)
        self.save_to_staging(source='zentao', entity_type='release', external_id=data['id'], payload=data, schema_version=self.SCHEMA_VERSION)
        return self._transform_release(product_id, data)

    def _transform_release(self, product_id: int, data: dict) -> ZenTaoRelease:
        """从原始数据转换并加载 Release。"""
        rel = self.session.query(ZenTaoRelease).filter_by(id=data['id']).first()
        if not rel:
            rel = ZenTaoRelease(id=data['id'], product_id=product_id)
            self.session.add(rel)
        rel.name = data.get('name')
        if data.get('date'):
            rel.date = datetime.fromisoformat(data['date'].replace(' ', 'T'))
        rel.status = data.get('status')
        rel.build_id = data.get('build')
        rel.opened_by = data.get('openedBy')
        if rel.opened_by:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', rel.opened_by)
            rel.opened_by_user_id = u.global_user_id
        rel.raw_data = data
        self.session.flush()
        return rel

    def _sync_action(self, product_id: int, data: dict) -> ZenTaoAction:
        '''"""TODO: Add description.

Args:
    self: TODO
    product_id: TODO
    data: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        action = self.session.query(ZenTaoAction).filter_by(id=data['id']).first()
        if not action:
            action = ZenTaoAction(id=data['id'], product_id=product_id)
            self.session.add(action)
        action.object_type = data.get('objectType')
        action.object_id = data.get('objectID')
        action.actor = data.get('actor')
        if action.actor:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', action.actor)
            action.actor_user_id = u.global_user_id
        action.action = data.get('action')
        if data.get('date'):
            action.date = datetime.fromisoformat(data['date'].replace(' ', 'T'))
        action.comment = data.get('comment')
        action.raw_data = data
        self.session.flush()
        return action

    def _sync_org_structure(self) -> None:
        """同步禅道部门结构到公共 Organization 表。"""
        depts = self.client.get_departments()
        dept_map = {}
        for d in depts:
            org_id = f"zentao_dept_{d['id']}"
            org_name = d['name']
            org = self.session.query(Organization).filter_by(org_id=org_id, is_current=True).first()
            if not org:
                org = Organization(org_id=org_id, org_name=org_name, org_level=3, is_current=True, sync_version=1)
                self.session.add(org)
                logger.info(f'Created ZenTao Organization: {org_name}')
            elif org.org_name != org_name:
                org = close_current_and_insert_new(self.session, Organization, {'org_id': org_id}, {'org_name': org_name, 'sync_version': org.sync_version, 'org_level': 3})
                logger.info(f'Updated ZenTao Organization Name: {org_name}')
            dept_map[d['id']] = org
        self.session.flush()
        for d in depts:
            if d.get('parent') and d['parent'] in dept_map:
                dept_map[d['id']].parent_org_id = dept_map[d['parent']].org_id
        self.session.flush()

    def _sync_zentao_users(self) -> None:
        """同步禅道用户到公共 User 表，并绑定部门。"""
        zt_users = self.client.get_users()
        for u_data in zt_users:
            user = IdentityManager.get_or_create_user(self.session, source='zentao', external_id=u_data['account'], email=u_data.get('email'), name=u_data.get('realname'))
            if user:
                if u_data.get('dept'):
                    org_id = f"zentao_dept_{u_data['dept']}"
                    org = self.session.query(Organization).filter_by(org_id=org_id, is_current=True).first()
                    if org:
                        user.department_id = org.org_id
                user.raw_data = u_data
        self.session.flush()
PluginRegistry.register_worker('zentao', ZenTaoWorker)
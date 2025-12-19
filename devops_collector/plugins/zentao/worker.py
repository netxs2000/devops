"""禅道 (ZenTao) 全量数据采集 Worker"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from devops_collector.models.base_models import Organization, User as GlobalUser, IdentityMapping

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from devops_collector.core.identity_manager import IdentityManager
from .client import ZenTaoClient
from .models import (
    ZenTaoProduct, ZenTaoExecution, ZenTaoIssue, ZenTaoProductPlan,
    ZenTaoTestCase, ZenTaoTestResult, ZenTaoBuild, ZenTaoRelease, ZenTaoAction
)

logger = logging.getLogger(__name__)

class ZenTaoWorker(BaseWorker):
    """禅道全量数据采集 Worker。"""
    
    def __init__(self, session: Session, client: ZenTaoClient):
        super().__init__(session, client)

    def process_task(self, task: dict) -> None:
        """处理禅道同步任务。"""
        product_id = task.get('product_id')
        logger.info(f"Processing ZenTao full-scale task: product_id={product_id}")
        
        try:
            # 1. 同步产品信息
            product = self._sync_product(product_id)
            if not product:
                return

            # 1.5 同步组织架构 (部门与人员)
            self._sync_org_structure()
            self._sync_zentao_users()

            # 2. 同步产品计划 (Plans)
            plans_data = self.client.get_plans(product.id)
            for p_data in plans_data:
                self._sync_plan(product.id, p_data)

            # 3. 同步执行 (Executions/迭代)
            executions_data = self.client.get_executions() # 此处可根据需要过滤项目
            for e_data in executions_data:
                # 简单过滤归属于当前产品的执行 (禅道 API 逻辑可能需要具体调整)
                self._sync_execution(product.id, e_data)

            # 3. 同步需求 (Stories) -> Issue
            stories = self.client.get_stories(product.id)
            for s_data in stories:
                self._sync_issue(product.id, s_data, 'feature')

            # 4. 同步缺陷 (Bugs) -> Issue
            bugs = self.client.get_bugs(product.id)
            for b_data in bugs:
                self._sync_issue(product.id, b_data, 'bug')

            # 5. 同步测试用例与结果
            test_cases = self.client.get_test_cases(product.id)
            for tc_data in test_cases:
                tc = self._sync_test_case(product.id, tc_data)
                results = self.client.get_test_results(tc.id)
                for r_data in results:
                    self._sync_test_result(tc.id, r_data)

            # 6. 同步发布 (Release)
            releases = self.client.get_releases(product.id)
            for rel_data in releases:
                self._sync_release(product.id, rel_data)

            # 7. 同步构建 (Build) - 遍历该产品的执行来获取
            product_executions = self.session.query(ZenTaoExecution).filter_by(product_id=product.id).all()
            for exec_item in product_executions:
                builds = self.client.get_builds(exec_item.id)
                for b_data in builds:
                    self._sync_build(product.id, exec_item.id, b_data)

            # 8. 同步操作日志 (Action Logs)
            actions = self.client.get_actions(product.id)
            for a_data in actions:
                self._sync_action(product.id, a_data)

            product.last_synced_at = datetime.now(timezone.utc)
            product.sync_status = 'COMPLETED'
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to sync ZenTao product {product_id}: {e}")
            raise

    def _sync_product(self, product_id: int) -> Optional[ZenTaoProduct]:
        product = self.session.query(ZenTaoProduct).filter_by(id=product_id).first()
        if not product:
            response = self.client._get(f"/products/{product_id}")
            p_data = response.json()
            product = ZenTaoProduct(
                id=p_data['id'],
                name=p_data['name'],
                code=p_data.get('code'),
                description=p_data.get('description'),
                status=p_data.get('status'),
                raw_data=p_data
            )
            self.session.add(product)
            self.session.flush()
        return product

    def _sync_execution(self, product_id: int, data: dict) -> ZenTaoExecution:
        exe = self.session.query(ZenTaoExecution).filter_by(id=data['id']).first()
        if not exe:
            exe = ZenTaoExecution(id=data['id'], product_id=product_id)
            self.session.add(exe)
        
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
        plan = self.session.query(ZenTaoProductPlan).filter_by(id=data['id']).first()
        if not plan:
            plan = ZenTaoProductPlan(id=data['id'], product_id=product_id)
            self.session.add(plan)
        
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
            plan.opened_by_user_id = u.id
            
        if data.get('openedDate'):
            plan.opened_date = datetime.fromisoformat(data['openedDate'].replace(' ', 'T'))
        
        plan.raw_data = data
        self.session.flush()
        return plan

    def _sync_issue(self, product_id: int, data: dict, issue_type: str) -> ZenTaoIssue:
        issue = self.session.query(ZenTaoIssue).filter_by(id=data['id'], type=issue_type).first()
        if not issue:
            issue = ZenTaoIssue(id=data['id'], product_id=product_id, type=issue_type)
            self.session.add(issue)
        
        issue.plan_id = data.get('plan') # 禅道返回的 plan ID
        issue.title = data.get('title') or data.get('name')
        issue.status = data.get('status')
        issue.priority = data.get('priority')
        issue.opened_by = data.get('openedBy')
        if issue.opened_by:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', issue.opened_by)
            issue.opened_by_user_id = u.id
            
        issue.assigned_to = data.get('assignedTo')
        if issue.assigned_to:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', issue.assigned_to)
            issue.assigned_to_user_id = u.id
            issue.user_id = u.id # 向后兼容
        
        if data.get('openedDate'):
            issue.created_at = datetime.fromisoformat(data['openedDate'].replace(' ', 'T'))
        if data.get('lastEditedDate'):
            issue.updated_at = datetime.fromisoformat(data['lastEditedDate'].replace(' ', 'T'))
        if data.get('closedDate'):
            issue.closed_at = datetime.fromisoformat(data['closedDate'].replace(' ', 'T'))
            
        issue.raw_data = data
        self.session.flush()
        return issue

    def _sync_test_case(self, product_id: int, data: dict) -> ZenTaoTestCase:
        tc = self.session.query(ZenTaoTestCase).filter_by(id=data['id']).first()
        if not tc:
            tc = ZenTaoTestCase(id=data['id'], product_id=product_id)
            self.session.add(tc)
        
        tc.title = data.get('title')
        tc.type = data.get('type')
        tc.status = data.get('status')
        tc.last_run_result = data.get('lastRunResult')
        tc.opened_by = data.get('openedBy')
        if tc.opened_by:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', tc.opened_by)
            tc.opened_by_user_id = u.id
            
        if data.get('openedDate'):
            tc.opened_date = datetime.fromisoformat(data['openedDate'].replace(' ', 'T'))
        tc.raw_data = data
        self.session.flush()
        return tc

    def _sync_test_result(self, case_id: int, data: dict) -> ZenTaoTestResult:
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
        build = self.session.query(ZenTaoBuild).filter_by(id=data['id']).first()
        if not build:
            build = ZenTaoBuild(id=data['id'], product_id=product_id, execution_id=execution_id)
            self.session.add(build)
        
        build.name = data.get('name')
        build.builder = data.get('builder')
        if build.builder:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', build.builder)
            build.builder_user_id = u.id
            
        if data.get('date'):
            build.date = datetime.fromisoformat(data['date'].replace(' ', 'T'))
        build.raw_data = data
        self.session.flush()
        return build

    def _sync_release(self, product_id: int, data: dict) -> ZenTaoRelease:
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
            rel.opened_by_user_id = u.id
        rel.raw_data = data
        self.session.flush()
        return rel

    def _sync_action(self, product_id: int, data: dict) -> ZenTaoAction:
        action = self.session.query(ZenTaoAction).filter_by(id=data['id']).first()
        if not action:
            action = ZenTaoAction(id=data['id'], product_id=product_id)
            self.session.add(action)
        
        action.object_type = data.get('objectType')
        action.object_id = data.get('objectID')
        action.actor = data.get('actor')
        if action.actor:
            u = IdentityManager.get_or_create_user(self.session, 'zentao', action.actor)
            action.actor_user_id = u.id
            
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
        # 建立 ID 映射，处理树形结构
        # 禅道部门 ID -> 系统 Organization 对象
        dept_map = {}
        
        # 第一遍：创建/更新所有部门
        for d in depts:
            org = self.session.query(Organization).filter_by(name=d['name']).first()
            if not org:
                org = Organization(name=d['name'], level='Department')
                self.session.add(org)
            dept_map[d['id']] = org
        
        self.session.flush()
        
        # 第二遍：建立父子关系
        for d in depts:
            if d.get('parent') and d['parent'] in dept_map:
                dept_map[d['id']].parent_id = dept_map[d['parent']].id
        
        self.session.flush()

    def _sync_zentao_users(self) -> None:
        """同步禅道用户到公共 User 表，并绑定部门。"""
        zt_users = self.client.get_users()
        for u_data in zt_users:
            IdentityManager.get_or_create_user(
                self.session, 
                source='zentao',
                external_id=u_data['account'],
                email=u_data.get('email'),
                name=u_data.get('realname')
            )
            # 更新部门属性 (对齐后的 User)
            user = self.session.query(GlobalUser).join(IdentityMapping).filter(
                IdentityMapping.source == 'zentao',
                IdentityMapping.external_id == u_data['account']
            ).first()
            
            if user:
                if u_data.get('dept'):
                    org = self.session.query(Organization).filter_by(name=u_data.get('dept_name')).first()
                    if org:
                        user.organization_id = org.id
                user.raw_data = u_data
                
        self.session.flush()

PluginRegistry.register_worker('zentao', ZenTaoWorker)

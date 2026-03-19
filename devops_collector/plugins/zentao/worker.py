"""禅道 (ZenTao) 全量数据采集 Worker"""

# from .client import ZenTaoClient
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.identity_manager import IdentityManager
from devops_collector.models import Organization, SyncLog

from .models import (
    ZenTaoAction,
    ZenTaoBuild,
    ZenTaoExecution,
    ZenTaoIssue,
    ZenTaoProduct,
    ZenTaoProductPlan,
    ZenTaoRelease,
    ZenTaoTestCase,
    ZenTaoTestResult,
)


logger = logging.getLogger(__name__)


def _safe_str(val: Any) -> str | None:
    """提取可能为字典的字段为主键字符串。"""
    if isinstance(val, dict):
        # 优先提取 account (用户), 其次 title/name (对象)
        return str(val.get("account") or val.get("id") or val.get("name") or val.get("title") or json.dumps(val))
    if isinstance(val, list):
        return json.dumps(val)
    return str(val) if val is not None and val != "" else None


def _safe_int(val: Any) -> int | None:
    """提取整数 ID，且将 "0" 视为 None (针对禅道外键关联)。"""
    s = _safe_str(val)
    if s is None or s == "0":
        return None
    try:
        # 有时 ID 可能包含非数字前缀（针对兼容逻辑）
        if isinstance(s, str) and "_" in s:
            s = s.split("_")[-1]
        return int(float(s))  # 先转 float 以兼容科学计数法或点号
    except Exception:
        return None


def _safe_date(val: Any) -> datetime | None:
    """容错处理禅道的不规范日期字符串 (如 '长期', '0000-00-00')。"""
    if not val or val == "长期" or val in ["0000-00-00", "0000-00-00 00:00:00"]:
        return None
    try:
        s = _safe_str(val).replace(" ", "T")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


SYNC_SINCE_DATE = datetime(2024, 1, 1)


def _is_after_cutoff(val: Any) -> bool:
    """判断给定日期是否在 2024-01-01 之后。如果没有日期，默认放行。"""
    dt = _safe_date(val)
    if not dt:
        return True
    if dt.tzinfo:
        dt = dt.replace(tzinfo=None)
    return dt >= SYNC_SINCE_DATE


class ZenTaoWorker(BaseWorker):
    """禅道全量数据采集 Worker。"""

    SCHEMA_VERSION = "1.0"

    def __init__(self, session: Session, client: Any, correlation_id: str = "unknown-cid", **kwargs):
        """初始化禅道 Worker。

        Args:
            session (Session): 数据库会话。
            client (Any): 禅道 API 客户端。
            correlation_id (str): 追踪 ID (用于日志对齐)
            **kwargs: 其他透传参数
        """
        super().__init__(session, client, correlation_id=correlation_id)

    def process_task(self, task: dict) -> None:
        """处理禅道同步任务。"""
        product_id = task.get("product_id")
        logger.info(f"Processing ZenTao full-scale task: product_id={product_id}")
        try:
            product = self._sync_product(product_id)
            if not product:
                return
            try:
                self._sync_org_structure()
            except Exception as e:
                logger.warning(f"Failed to sync ZenTao organization structure: {e}")

            try:
                self._sync_zentao_users()
            except Exception as e:
                logger.warning(f"Failed to sync ZenTao users: {e}")
            try:
                plans_data = self.client.get_plans(product.id)
                for p_data in plans_data:
                    self._sync_plan(product.id, p_data)
            except Exception as e:
                logger.error(f"Failed to sync plans for product {product_id}: {e}")
            # 2. 同步层级结构 (Program -> Project -> Execution)
            # 这是一个全局同步，因为它涉及到跨项目的层级
            logger.info("Syncing ZenTao hierarchy (Programs/Projects/Executions)...")

            # 2.1 同步项目集 Programs
            try:
                programs = self.client.get_programs()
                for p_data in programs:
                    self._sync_execution(product.id, p_data)
            except Exception as e:
                logger.warning(f"Failed to sync programs: {e}")

            # 2.2 同步项目 Projects
            try:
                projects = self.client.get_projects()
                for p_data in projects:
                    # 检查该项目是否关联到当前产品
                    linked_products = p_data.get("products", [])
                    p_id_list = []
                    if isinstance(linked_products, list):
                        for item in linked_products:
                            if isinstance(item, dict):
                                p_id_list.append(_safe_int(item.get("id")))
                            else:
                                p_id_list.append(_safe_int(item))

                    # 如果该项目关联到当前产品，或者它是全局的，我们就同步它
                    self._sync_execution(product.id if product.id in p_id_list else None, p_data)
            except Exception as e:
                logger.warning(f"Failed to sync projects: {e}")

            # 2.3 同步当前产品下的所有执行 Executions
            try:
                executions_data = self.client.get_executions(product_id=product.id)
                for e_data in executions_data:
                    self._sync_execution(product.id, e_data)
            except Exception as e:
                logger.error(f"Failed to sync executions for product {product_id}: {e}")
            # 3. 批量同步 Stories (Features) 和 Bugs
            try:
                stories = self.client.get_stories(product.id)
                story_batch = [s for s in stories if _is_after_cutoff(s.get("openedDate"))]
                if story_batch:
                    self._sync_issues_batch(product.id, story_batch, "feature")
                    self.session.commit()
            except Exception as e:
                self.session.rollback()
                logger.error(f"Failed to sync stories (features) for product {product_id}: {e}")

            try:
                bugs = self.client.get_bugs(product.id)
                bug_batch = [b for b in bugs if _is_after_cutoff(b.get("openedDate"))]
                if bug_batch:
                    self._sync_issues_batch(product.id, bug_batch, "bug")
                    self.session.commit()
            except Exception as e:
                self.session.rollback()
                logger.error(f"Failed to sync bugs for product {product_id}: {e}")

            # 4. 同步测试用例与结果
            try:
                test_cases = self.client.get_test_cases(product.id)
                for tc_data in test_cases:
                    if not _is_after_cutoff(tc_data.get("openedDate")):
                        continue
                    tc = self._sync_test_case(product.id, tc_data)
                    if not tc:
                        continue
                    try:
                        results = self.client.get_test_results(tc.id)
                        for r_data in results:
                            if _is_after_cutoff(r_data.get("date")):
                                self._sync_test_result(tc.id, r_data)
                    except Exception as res_e:
                        logger.debug(f"Failed to sync results for case {tc.id}: {res_e}")
            except Exception as case_e:
                logger.warning(f"Failed to sync test cases for product {product_id}: {case_e}")

            product_executions = self.session.query(ZenTaoExecution).filter_by(product_id=product.id).all()
            for exec_item in product_executions:
                # 同步构建 (Builds)
                try:
                    builds = self.client.get_builds(exec_item.id)
                    for b_data in builds:
                        if _is_after_cutoff(b_data.get("date")):
                            self._sync_build(product.id, exec_item.id, b_data)
                except Exception as e:
                    logger.warning(f"Failed to sync builds for execution {exec_item.id}: {e}")

                # 批量同步任务 (Tasks)
                try:
                    tasks = self.client.get_tasks(exec_item.id)
                    task_batch = [t for t in tasks if _is_after_cutoff(t.get("openedDate"))]
                    if task_batch:
                        self._sync_tasks_batch(product.id, exec_item.id, task_batch)
                        self.session.commit()
                except Exception as e:
                    self.session.rollback()
                    logger.error(f"Failed to sync tasks for execution {exec_item.id}: {e}")

            # 5. 同步发布 (Releases)
            try:
                releases = self.client.get_releases(product.id)
                for rel_data in releases:
                    if _is_after_cutoff(rel_data.get("date")):
                        self._sync_release(product.id, rel_data)
            except Exception as e:
                logger.warning(f"Failed to sync releases for product {product_id}: {e}")

            # 6. 同步操作日志 (Actions) - 经常 404
            try:
                actions = self.client.get_actions(product.id)
                for a_data in actions:
                    if _is_after_cutoff(a_data.get("date")):
                        self._sync_action(product.id, a_data)
            except Exception as e:
                logger.warning(f"Failed to sync actions (audit logs) for product {product_id}: {e}")

            product.last_synced_at = datetime.now(UTC)
            product.sync_status = "COMPLETED"

            # 记录成功日志
            msg = f"ZenTao product {product_id} synced successfully."
            self.session.add(
                SyncLog(
                    project_id=product.mdm_project_id if hasattr(product, "mdm_project_id") else None,
                    external_id=str(product_id),
                    source="zentao",
                    status="SUCCESS",
                    message=msg,
                    correlation_id=self.correlation_id,
                )
            )
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to sync ZenTao product {product_id}: {e}")

            # 记录失败状态
            try:
                # 重新开启 session 以防旧 session 损坏
                p_failed = self.session.query(ZenTaoProduct).filter_by(id=product_id).first()
                if p_failed:
                    p_failed.sync_status = "FAILED"
                    self.session.add(
                        SyncLog(
                            project_id=p_failed.mdm_project_id if hasattr(p_failed, "mdm_project_id") else None,
                            external_id=str(product_id),
                            source="zentao",
                            status="FAILED",
                            message=f"ZenTao sync failed: {str(e)[:500]}",
                            correlation_id=self.correlation_id,
                        )
                    )
                    self.session.commit()
            except Exception as inner_e:
                logger.error(f"Failed to record error status for product {product_id}: {inner_e}")
            raise

    def _sync_product(self, product_id: int) -> ZenTaoProduct | None:
        """同步禅道产品的元数据。

        Args:
            product_id (int): 禅道产品 ID。

        Returns:
            Optional[ZenTaoProduct]: 同步后的产品模型对象。
        """
        product = self.session.query(ZenTaoProduct).filter_by(id=product_id).first()
        if not product:
            response = self.client._get(f"products/{product_id}")
            p_data = response.json()
            self.save_to_staging(
                source="zentao",
                entity_type="product",
                external_id=product_id,
                payload=p_data,
                schema_version=self.SCHEMA_VERSION,
            )
            product = ZenTaoProduct(
                id=p_data["id"],
                name=p_data.get("name") or f"Untitled Product {p_data['id']}",
                code=p_data.get("code"),
                description=p_data.get("description"),
                status=p_data.get("status"),
                raw_data=p_data,
            )
            self.session.add(product)
            self.session.flush()
        return product

    def _sync_execution(self, product_id: int | None, data: dict) -> ZenTaoExecution:
        """同步禅道层级节点（项目集/项目/迭代/阶段）。

        Args:
            product_id: 关联的产品 ID。如果是项目集或全局项目，可能为 None。
            data: API 返回的原始数据。
        """
        exe = self.session.query(ZenTaoExecution).filter_by(id=data["id"]).first()
        if not exe:
            exe = ZenTaoExecution(id=data["id"], product_id=product_id)
            self.session.add(exe)
        self.save_to_staging(
            source="zentao",
            entity_type="execution",
            external_id=data["id"],
            payload=data,
            schema_version=self.SCHEMA_VERSION,
        )
        exe.name = data.get("name") or f"Untitled {data.get('type', 'Execution')} {data['id']}"
        exe.code = data.get("code")
        exe.type = data.get("type")
        exe.status = data.get("status")
        exe.parent_id = _safe_int(data.get("parent"))
        exe.path = data.get("path")

        # 只有在明确提供或者原本没值的情况下更新 product_id
        if product_id and not exe.product_id:
            exe.product_id = product_id
        elif not exe.product_id:
            # 尝试从数据中提取第一个产品
            linked_products = data.get("products", [])
            if linked_products:
                first_p = linked_products[0]
                p_id = _safe_int(first_p.get("id")) if isinstance(first_p, dict) else _safe_int(first_p)
                if p_id:
                    exe.product_id = p_id

        # 如果还是没找到 product_id，为了满足非空约束，可能需要跳过或填一个默认值
        # 但禅道中有些节点确实没有 product_id (如顶级 Program)，我们需要确认模型是否允许为 null
        # 模型中 product_id 是 nullable=False。这可能是一个设计缺陷，因为 Program 不属于 Product。
        if not exe.product_id:
            # 暂时归口，如果全局节点不属于任何产品，则设为 None (已改为 nullable)
            exe.product_id = product_id if product_id is not None else None

        exe.begin = _safe_date(data.get("begin"))
        exe.end = _safe_date(data.get("end"))
        exe.raw_data = data
        self.session.flush()
        return exe

    def _sync_plan(self, product_id: int, data: dict) -> ZenTaoProductPlan:
        """同步禅道产品计划记录。

        Args:
            product_id (int): 所属产品 ID。
            data (dict): 原始计划数据。

        Returns:
            ZenTaoProductPlan: 同步后的计划模型对象。
        """
        plan = self.session.query(ZenTaoProductPlan).filter_by(id=data["id"]).first()
        if not plan:
            plan = ZenTaoProductPlan(id=data["id"], product_id=product_id)
            self.session.add(plan)
        self.save_to_staging(
            source="zentao",
            entity_type="plan",
            external_id=data["id"],
            payload=data,
            schema_version=self.SCHEMA_VERSION,
        )
        plan.title = data.get("title") or f"Untitled Plan {data['id']}"
        plan.begin = _safe_date(data.get("begin"))
        plan.end = _safe_date(data.get("end"))
        plan.status = data.get("status")
        plan.desc = data.get("desc")
        plan.opened_by = _safe_str(data.get("openedBy"))
        if plan.opened_by:
            u = IdentityManager.get_or_create_user(self.session, "zentao", plan.opened_by)
            if u:
                plan.opened_by_user_id = u.global_user_id
        if data.get("openedDate"):
            plan.opened_date = datetime.fromisoformat(data["openedDate"].replace(" ", "T"))
        plan.raw_data = data
        self.session.flush()
        return plan

    def _sync_issues_batch(self, product_id: int, batch: list[dict], issue_type: str) -> None:
        """批量同步禅道问题 (Stories/Bugs)：Staging + Transform 均走批处理。"""
        if not batch:
            return

        # 1. 批量 Staging (COPY FROM)
        self.bulk_save_to_staging("zentao", f"issue_{issue_type}", batch)

        # 2. 批量 Transform：预加载已存在的记录
        batch_ids = [d["id"] for d in batch]
        existing = self.session.query(ZenTaoIssue).filter(ZenTaoIssue.id.in_(batch_ids), ZenTaoIssue.type == issue_type).all()
        existing_map = {i.id: i for i in existing}

        for data in batch:
            issue = existing_map.get(data["id"])
            if issue_type == "feature":
                est = data.get("estimate")
                payload_est = est if isinstance(est, (dict, list)) else str(est)
            else:
                payload_est = None

            issue_title = _safe_str(data.get("title") or data.get("name")) or f"Untitled {issue_type.capitalize()} {data['id']}"

            if not issue:
                issue = ZenTaoIssue(id=data["id"], product_id=product_id, type=issue_type, title=issue_title)
                if payload_est:
                    issue.estimate = payload_est
                self.session.add(issue)
            else:
                issue.title = issue_title
                if payload_est:
                    issue.estimate = payload_est

            issue.priority = _safe_int(data.get("priority") or data.get("pri"))

            opened = _safe_str(data.get("openedBy"))
            issue.opened_by = str(opened) if opened else None
            if opened:
                u = IdentityManager.get_or_create_user(self.session, "zentao", opened)
                if u:
                    issue.opened_by_user_id = u.global_user_id

            assigned = _safe_str(data.get("assignedTo"))
            issue.assigned_to = str(assigned) if assigned else None
            if assigned:
                u = IdentityManager.get_or_create_user(self.session, "zentao", assigned)
                if u:
                    issue.assigned_to_user_id = u.global_user_id
                    issue.user_id = u.global_user_id

            if data.get("openedDate"):
                try:
                    issue.created_at = datetime.fromisoformat(str(data["openedDate"]).replace(" ", "T"))
                except Exception:
                    pass
            if data.get("lastEditedDate"):
                try:
                    issue.updated_at = datetime.fromisoformat(str(data["lastEditedDate"]).replace(" ", "T"))
                except Exception:
                    pass
            if data.get("closedDate"):
                try:
                    issue.closed_at = datetime.fromisoformat(str(data["closedDate"]).replace(" ", "T"))
                except Exception:
                    pass
            issue.raw_data = data

        # 3. 批量 flush 一次，替代逐条 flush
        self.session.flush()
        logger.info(f"Batch synced {len(batch)} {issue_type}(s) for product {product_id}")

    def _sync_issue(self, product_id: int, data: dict, issue_type: str) -> ZenTaoIssue:
        """同步禅道问题（单条兼容接口，内部转发到批量）。"""
        self._sync_issues_batch(product_id, [data], issue_type)

    def _sync_tasks_batch(self, product_id: int, execution_id: int, batch: list[dict]) -> None:
        """批量同步禅道任务 (Tasks)：Staging + Transform 均走批处理。"""
        if not batch:
            return

        # 1. 批量 Staging (COPY FROM)
        self.bulk_save_to_staging("zentao", "task", batch)

        # 2. 批量 Transform：预加载已存在的记录
        batch_ids = [d["id"] for d in batch]
        existing = self.session.query(ZenTaoIssue).filter(ZenTaoIssue.id.in_(batch_ids), ZenTaoIssue.type == "task").all()
        existing_map = {i.id: i for i in existing}

        for data in batch:
            issue = existing_map.get(data["id"])
            issue_title = _safe_str(data.get("name") or data.get("title")) or f"Untitled Task {data['id']}"

            if not issue:
                real_exe_id = _safe_int(execution_id)
                issue = ZenTaoIssue(id=data["id"], product_id=product_id, execution_id=real_exe_id, type="task", title=issue_title)
                self.session.add(issue)
            else:
                issue.title = issue_title

            issue.status = _safe_str(data.get("status"))
            issue.priority = _safe_int(data.get("pri") or data.get("priority"))
            issue.task_type = _safe_str(data.get("type"))

            est = data.get("estimate")
            issue.estimate = est if isinstance(est, (dict, list)) else str(est)
            con = data.get("consumed")
            issue.consumed = con if isinstance(con, (dict, list)) else str(con)
            lft = data.get("left")
            issue.left = lft if isinstance(lft, (dict, list)) else str(lft)

            opened = _safe_str(data.get("openedBy"))
            issue.opened_by = str(opened) if opened else None
            if opened:
                u = IdentityManager.get_or_create_user(self.session, "zentao", opened)
                if u:
                    issue.opened_by_user_id = u.global_user_id

            assigned = _safe_str(data.get("assignedTo"))
            issue.assigned_to = str(assigned) if assigned else None
            if assigned:
                u = IdentityManager.get_or_create_user(self.session, "zentao", assigned)
                if u:
                    issue.assigned_to_user_id = u.global_user_id

            if data.get("openedDate"):
                try:
                    issue.created_at = datetime.fromisoformat(str(data["openedDate"]).replace(" ", "T"))
                except Exception:
                    pass
            if data.get("finishedDate"):
                try:
                    issue.closed_at = datetime.fromisoformat(str(data["finishedDate"]).replace(" ", "T"))
                except Exception:
                    pass
            issue.raw_data = data

        # 3. 批量 flush 一次
        self.session.flush()
        logger.info(f"Batch synced {len(batch)} task(s) for execution {execution_id}")

    def _sync_task(self, product_id: int, execution_id: int, data: dict) -> ZenTaoIssue:
        """同步禅道任务（单条兼容接口，内部转发到批量）。"""
        self._sync_tasks_batch(product_id, execution_id, [data])

    def _transform_task(self, product_id: int, execution_id: int, data: dict) -> ZenTaoIssue:
        """将禅道 Task 转换为 ZenTaoIssue(type='task')。"""
        issue = self.session.query(ZenTaoIssue).filter_by(id=data["id"], type="task").first()
        # 预先提取标题
        issue_title = _safe_str(data.get("name") or data.get("title")) or f"Untitled Task {data['id']}"

        if not issue:
            # 强化：如果传入的 execution_id 为 0，视为 None
            real_exe_id = _safe_int(execution_id)
            issue = ZenTaoIssue(id=data["id"], product_id=product_id, execution_id=real_exe_id, type="task", title=issue_title)
            self.session.add(issue)
        else:
            issue.title = issue_title

        issue.status = _safe_str(data.get("status"))
        issue.priority = _safe_int(data.get("pri") or data.get("priority"))
        issue.task_type = _safe_str(data.get("type"))  # devel, design 等

        # 工时数据 (FinOps 核心)
        est = data.get("estimate")
        issue.estimate = est if isinstance(est, (dict, list)) else str(est)

        con = data.get("consumed")
        issue.consumed = con if isinstance(con, (dict, list)) else str(con)

        lft = data.get("left")
        issue.left = lft if isinstance(lft, (dict, list)) else str(lft)

        # 人员映射
        opened = _safe_str(data.get("openedBy"))
        issue.opened_by = str(opened) if opened else None
        if opened:
            u = IdentityManager.get_or_create_user(self.session, "zentao", opened)
            if u:
                issue.opened_by_user_id = u.global_user_id

        assigned = _safe_str(data.get("assignedTo"))
        issue.assigned_to = str(assigned) if assigned else None
        if assigned:
            u = IdentityManager.get_or_create_user(self.session, "zentao", assigned)
            if u:
                issue.assigned_to_user_id = u.global_user_id

        # 时间映射
        if data.get("openedDate"):
            try:
                issue.created_at = datetime.fromisoformat(str(data["openedDate"]).replace(" ", "T"))
            except Exception:
                pass
        if data.get("finishedDate"):
            try:
                issue.closed_at = datetime.fromisoformat(str(data["finishedDate"]).replace(" ", "T"))
            except Exception:
                pass

        issue.raw_data = data
        self.session.flush()
        return issue

    def _sync_test_case(self, product_id: int, data: dict) -> ZenTaoTestCase:
        """同步禅道测试用例记录。

        Args:
            product_id (int): 关联产品 ID。
            data (dict): 原始用例数据。

        Returns:
            ZenTaoTestCase: 同步后的用例模型对象。
        """
        # 兼容 API 可能会返回字符串 id (如 "case_23461") 的情况
        tc_id = _safe_int(data.get("caseID") or data.get("id"))
        if not tc_id:
            return None  # 无法提取有效 ID

        tc = self.session.query(ZenTaoTestCase).filter_by(id=tc_id).first()
        if not tc:
            tc = ZenTaoTestCase(id=tc_id, product_id=product_id)
            self.session.add(tc)
        self.save_to_staging(
            source="zentao",
            entity_type="test_case",
            external_id=tc_id,
            payload=data,
            schema_version=self.SCHEMA_VERSION,
        )
        tc.title = data.get("title") or f"Untitled Case {tc_id}"
        tc.type = data.get("type")
        tc.status = data.get("status")
        # 自动化关联：提取关联的需求 ID (Story ID)
        tc.story_id = _safe_int(data.get("story"))
        tc.last_run_result = data.get("lastRunResult")
        tc.opened_by = _safe_str(data.get("openedBy"))
        if tc.opened_by:
            u = IdentityManager.get_or_create_user(self.session, "zentao", tc.opened_by)
            if u:
                tc.opened_by_user_id = u.global_user_id
        if data.get("openedDate"):
            tc.opened_date = datetime.fromisoformat(data["openedDate"].replace(" ", "T"))
        tc.raw_data = data
        self.session.flush()
        return tc

    def _sync_test_result(self, case_id: int, data: dict) -> ZenTaoTestResult:
        """同步禅道测试执行结果记录。

        Args:
            case_id (int): 关联用例的 ID。
            data (dict): 原始测试结果数据。

        Returns:
            ZenTaoTestResult: 同步后的测试结果模型对象。
        """
        res = self.session.query(ZenTaoTestResult).filter_by(id=data["id"]).first()
        if not res:
            res = ZenTaoTestResult(id=data["id"], case_id=case_id)
            self.session.add(res)
        res.result = data.get("caseResult")
        if data.get("date"):
            res.date = datetime.fromisoformat(data["date"].replace(" ", "T"))
        res.last_run_by = _safe_str(data.get("lastRunBy"))
        res.raw_data = data
        self.session.flush()
        return res

    def _sync_build(self, product_id: int, execution_id: int, data: dict) -> ZenTaoBuild:
        """同步禅道构建/版本记录。

        Args:
            product_id (int): 所属产品 ID。
            execution_id (int): 关联执行 ID。
            data (dict): 原始构建数据。

        Returns:
            ZenTaoBuild: 同步后的构建模型对象。
        """
        build = self.session.query(ZenTaoBuild).filter_by(id=data["id"]).first()
        if not build:
            build = ZenTaoBuild(id=data["id"], product_id=product_id, execution_id=execution_id)
            self.session.add(build)
        self.save_to_staging(
            source="zentao",
            entity_type="build",
            external_id=data["id"],
            payload=data,
            schema_version=self.SCHEMA_VERSION,
        )
        return self._transform_build(product_id, execution_id, data)

    def _transform_build(self, product_id: int, execution_id: int, data: dict) -> ZenTaoBuild:
        """从原始数据转换并加载 Build。"""
        build = self.session.query(ZenTaoBuild).filter_by(id=data["id"]).first()
        if not build:
            build = ZenTaoBuild(id=data["id"], product_id=product_id, execution_id=execution_id)
            self.session.add(build)
        build.name = data.get("name") or f"Untitled Build {data['id']}"
        builder = _safe_str(data.get("builder"))
        build.builder = str(builder) if builder else None
        if build.builder:
            u = IdentityManager.get_or_create_user(self.session, "zentao", builder)
            if u:
                build.builder_user_id = u.global_user_id
        if data.get("date"):
            build.date = datetime.fromisoformat(str(data["date"]).replace(" ", "T"))
        build.raw_data = data
        self.session.flush()
        return build

    def _sync_release(self, product_id: int, data: dict) -> ZenTaoRelease:
        """同步禅道发布记录。

        Args:
            product_id (int): 产品 ID。
            data (dict): 原始发布数据。

        Returns:
            ZenTaoRelease: 同步后的发布模型对象。
        """
        rel = self.session.query(ZenTaoRelease).filter_by(id=data["id"]).first()
        if not rel:
            rel = ZenTaoRelease(id=data["id"], product_id=product_id)
            self.session.add(rel)
        self.save_to_staging(
            source="zentao",
            entity_type="release",
            external_id=data["id"],
            payload=data,
            schema_version=self.SCHEMA_VERSION,
        )
        return self._transform_release(product_id, data)

    def _transform_release(self, product_id: int, data: dict) -> ZenTaoRelease:
        """从原始数据转换并加载 Release。不再在此处尝试自动推导计划。"""
        rel = self.session.query(ZenTaoRelease).filter_by(id=data["id"]).first()
        if not rel:
            rel = ZenTaoRelease(id=data["id"], product_id=product_id)
            self.session.add(rel)

        rel.name = data.get("name") or f"Untitled Release {data['id']}"
        if data.get("date"):
            rel.date = datetime.fromisoformat(str(data["date"]).replace(" ", "T"))
        rel.status = data.get("status")
        b_val = data.get("build")
        build_id_val = _safe_int(b_val if not isinstance(b_val, dict) else b_val.get("id"))
        if build_id_val:
            # 建立桩数据以防外键报错，并且必须在赋值 rel.build_id 之前执行，防止 autoflush
            existing_b = self.session.query(ZenTaoBuild).filter_by(id=build_id_val).first()
            if not existing_b:
                b_name = b_val.get("name") if isinstance(b_val, dict) else str(build_id_val)
                stub_b = ZenTaoBuild(id=build_id_val, product_id=product_id, name=b_name)
                self.session.add(stub_b)
                self.session.flush()  # 先推入数据库
            rel.build_id = build_id_val
        else:
            rel.build_id = None

        # 业务韧性：仅同步 API 直接提供的计划关联且必须物理存在
        plan_id = _safe_int(data.get("plan"))
        if plan_id:
            existing_plan = self.session.query(ZenTaoProductPlan).filter_by(id=plan_id).first()
            if not existing_plan:
                logger.warning(f"Plan {plan_id} not found for release {data.get('id')}, setting to NULL.")
                plan_id = None
        rel.plan_id = plan_id

        opened = _safe_str(data.get("openedBy"))
        rel.opened_by = str(opened) if opened else None
        if rel.opened_by:
            u = IdentityManager.get_or_create_user(self.session, "zentao", opened)
            if u:
                rel.opened_by_user_id = u.global_user_id

        rel.raw_data = data
        self.session.flush()
        return rel

    def _sync_action(self, product_id: int, data: dict) -> ZenTaoAction:
        """同步禅道操作日志记录。

        Args:
            product_id (int): 产品 ID。
            data (dict): 原始操作日志数据。

        Returns:
            ZenTaoAction: 同步后的操作日志模型对象。
        """
        action = self.session.query(ZenTaoAction).filter_by(id=data["id"]).first()
        if not action:
            action = ZenTaoAction(id=data["id"], product_id=product_id)
            self.session.add(action)
        action.object_type = data.get("objectType")
        action.object_id = data.get("objectID")
        actor = _safe_str(data.get("actor"))
        action.actor = str(actor) if actor else None
        if action.actor:
            u = IdentityManager.get_or_create_user(self.session, "zentao", actor)
            if u:
                action.actor_user_id = u.global_user_id
        action.action = data.get("action")
        if data.get("date"):
            action.date = datetime.fromisoformat(data["date"].replace(" ", "T"))
        action.comment = data.get("comment")
        action.raw_data = data
        self.session.flush()
        return action

    def _sync_org_structure(self) -> None:
        """同步禅道部门结构到公共 Organization 表。"""
        depts = self.client.get_departments()
        dept_map = {}
        for d in depts:
            org_id = f"zentao_dept_{d['id']}"
            org_name = d["name"]
            # 即使 is_current=False 的历史数据也会触发唯一索引冲突，所以必须全局查询
            org = self.session.query(Organization).filter_by(org_id=org_id).first()
            if not org:
                try:
                    with self.session.begin_nested():
                        org = Organization(org_id=org_id, org_name=org_name, org_level=3, is_current=True, sync_version=1)
                        self.session.add(org)
                        self.session.flush()
                        logger.info(f"Created ZenTao Organization: {org_name}")
                except Exception:
                    self.session.rollback()
                    org = self.session.query(Organization).filter_by(org_id=org_id).first()
            elif org.org_name != org_name:
                org.org_name = org_name
                logger.info(f"Updated ZenTao Organization Name: {org_name}")
            dept_map[d["id"]] = org
        self.session.flush()
        for d in depts:
            if d.get("parent") and d["parent"] in dept_map:
                dept_map[d["id"]].parent_org_id = dept_map[d["parent"]].org_id
        self.session.flush()

    def _sync_zentao_users(self) -> None:
        """同步禅道用户到公共 User 表，并绑定部门。"""
        zt_users = self.client.get_users()
        for u_data in zt_users:
            user = IdentityManager.get_or_create_user(
                self.session,
                source="zentao",
                external_id=u_data["account"],
                email=u_data.get("email"),
                name=u_data.get("realname"),
            )
            if user:
                if u_data.get("dept"):
                    org_id = f"zentao_dept_{u_data['dept']}"
                    org = self.session.query(Organization).filter_by(org_id=org_id).first()
                    if org:
                        user.department_id = org.org_id
                user.raw_data = u_data
        self.session.flush()

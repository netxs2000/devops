"""企业微信 (WeCom) 数据采集 Worker

严格遵循 contexts.md 17.2 节 MDM 六大金科玉律：
1. 原始数据先落 Staging (save_to_staging)
2. 部门通过 OrganizationService 统一 Upsert (含 manager_raw_id 延迟对齐)
3. 人员通过 IdentityManager 进行 OneID 映射
4. 所有写入携带 source_system='wecom' 血缘标记
5. 批次结束后触发 realign_all_managers 异步自愈
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.identity_manager import IdentityManager
from devops_collector.core.organization_service import OrganizationService
from devops_collector.core.registry import PluginRegistry
from devops_collector.core.utils import safe_id

logger = logging.getLogger(__name__)


class WeComWorker(BaseWorker):
    """企业微信通讯录同步 Worker。

    同步流程 (严格按顺序执行):
        Phase 1: 部门拓扑同步 (Upsert)
        Phase 2: 人员身份同步 (OneID 映射)
        Phase 3: 负责人异步对齐 (Self-Healing)
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self, session: Session, client: Any = None, correlation_id: str = "unknown-cid", **kwargs) -> None:
        """初始化企业微信 Worker。

        Args:
            session: SQLAlchemy 数据库会话。
            client: WeComClient 实例。
            correlation_id: 追踪 ID (用于日志对齐)。
        """
        if client is None:
            raise ValueError("WeComClient must be provided")
        super().__init__(session, client, correlation_id=correlation_id)
        self.org_service = OrganizationService(session)
        self.excluded_ids = set(kwargs.get("excluded_departments", []))

    def process_task(self, task: dict) -> dict:
        """核心同步逻辑。

        Args:
            task: 任务字典，可包含:
                - sync_scope: 'full' (全量) 或 'departments_only' / 'users_only'

        Returns:
            同步统计摘要字典。
        """
        scope = task.get("sync_scope", "full")
        stats = {"departments": 0, "users": 0, "realigned": 0}

        logger.info(f"[WeCom] Starting sync (scope={scope}, cid={self.correlation_id})")

        # ── Phase 1: 部门拓扑同步 ──
        if scope in ("full", "departments_only"):
            stats["departments"] = self._sync_departments()

        # ── Phase 2: 人员身份同步 ──
        if scope in ("full", "users_only"):
            stats["users"] = self._sync_users()

        # ── Phase 3: 负责人异步对齐 (自愈) ──
        if scope == "full":
            stats["realigned"] = self._realign_managers()

        logger.info(f"[WeCom] Sync completed: {stats}")
        return stats

    # ─────────────────────────────────────
    #  Phase 1: 部门拓扑同步
    # ─────────────────────────────────────

    def _sync_departments(self) -> int:
        """同步企业微信部门树到 mdm_organizations。"""
        departments = self.client.get_departments()
        count = 0

        filtered = self._filter_departments(departments)

        for dept in filtered:
            dept_id = safe_id(dept.get("id"))
            dept_name = dept.get("name", "")
            parent_raw = safe_id(dept.get("parentid"))

            self.save_to_staging(
                source="wecom",
                entity_type="department",
                external_id=dept_id,
                payload=dept,
                schema_version=self.SCHEMA_VERSION,
            )

            leader_userid = None
            try:
                detail = self.client.get_department_detail(dept_id)
                if detail:
                    leaders = detail.get("department_leader", [])
                    if leaders:
                        leader_userid = leaders[0] if isinstance(leaders, list) else leaders
            except Exception as e:
                logger.debug(f"[WeCom] Could not fetch detail for dept {dept_id}: {e}")

            parent_code = f"wecom_dept_{parent_raw}" if parent_raw else None
            self.org_service.upsert_organization(
                org_code=f"wecom_dept_{dept_id}",
                org_name=dept_name,
                org_level=self._infer_org_level(dept),
                parent_org_code=parent_code,
                manager_raw_id=leader_userid,
                source="wecom",
            )
            count += 1

        self.session.flush()
        logger.info(f"[WeCom] Phase 1: {count} departments synced.")
        return count

    def _filter_departments(self, all_depts: list[dict]) -> list[dict]:
        """递归过滤黑名单部门及其子树。"""
        if not self.excluded_ids:
            return all_depts

        dept_map = {str(d["id"]): d for d in all_depts}
        
        def is_id_excluded(d_id: str) -> bool:
            if d_id in self.excluded_ids:
                return True
            curr = dept_map.get(d_id)
            if not curr: return False
            p_id = str(curr.get("parentid", "0"))
            if p_id == "0": return d_id in self.excluded_ids
            return is_id_excluded(p_id)

        filtered = [d for d in all_depts if not is_id_excluded(str(d["id"]))]
        return filtered

    def _infer_org_level(self, dept: dict) -> int:
        dept_id = dept.get("id")
        parent_id = dept.get("parentid", 0)
        return 1 if dept_id == 1 else (2 if parent_id in (0, 1) else 3)

    # ─────────────────────────────────────
    #  Phase 2: 人员身份同步
    # ─────────────────────────────────────

    def _sync_users(self) -> int:
        """主逻辑：仅同步非排除部门的人员。"""
        all_depts = self.client.get_departments()
        filtered_depts = self._filter_departments(all_depts)
        
        seen_ids: set[str] = set()
        count = 0

        for dept in filtered_depts:
            dept_id_int = int(dept["id"])
            u_list = self.client.get_department_users(dept_id_int)
            for u_data in u_list:
                userid = u_data.get("userid", "")
                if not userid or userid in seen_ids:
                    continue
                seen_ids.add(userid)
                
                name = u_data.get("name", "")
                email = u_data.get("email", "") or u_data.get("biz_mail", "")

                # 1. Staging
                self.save_to_staging(
                    source="wecom",
                    entity_type="user",
                    external_id=userid,
                    payload=u_data,
                    schema_version=self.SCHEMA_VERSION,
                )

                # 2. Identity Mapping (OneID)
                user = IdentityManager.get_or_create_user(
                    self.session,
                    source="wecom",
                    external_id=userid,
                    email=email,
                    name=name,
                    employee_id=u_data.get("employee_id"),
                    username=userid,
                    create_if_not_found=True,
                )

                if user:
                    # 3. Link Dept
                    depts_ids = u_data.get("department", [])
                    if depts_ids:
                        primary_dept_id = safe_id(depts_ids[0])
                        org = self.org_service.get_org_by_code(f"wecom_dept_{primary_dept_id}")
                        if org:
                            user.department_id = org.id

                    user.source_system = "wecom"
                    user.correlation_id = self.correlation_id
                    
                    if not user.position:
                        user.position = u_data.get("position", "")

                    count += 1

                if count % 200 == 0:
                    self.session.flush()

        self.session.flush()
        logger.info(f"[WeCom] Phase 2: {count} users synced.")
        return count

    # ─────────────────────────────────────
    #  Phase 3: 负责人异步对齐
    # ─────────────────────────────────────

    def _realign_managers(self) -> int:
        """执行全局负责人自愈对齐。
        
        在 Phase 1 & 2 完成后，所有 User 和 Organization 数据已入库。
        此时运行 realign 可以将 manager_raw_id 解析为实际的 manager_user_id。
        """
        stats = self.org_service.realign_all_managers()
        realigned_count = stats.get("success", 0)
        logger.info(f"[WeCom] Phase 3 complete: {realigned_count} managers realigned.")
        return realigned_count


PluginRegistry.register_worker("wecom", WeComWorker)

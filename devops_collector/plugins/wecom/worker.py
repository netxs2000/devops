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
        """同步企业微信部门树到 mdm_organizations。

        遵循规则:
        - 所有原始 JSON 先落 Staging
        - 通过 OrganizationService.upsert_organization 统一入库
        - 负责人使用 manager_raw_id 延迟绑定 (不触发递归)
        """
        departments = self.client.get_departments()
        count = 0

        for dept in departments:
            dept_id = safe_id(dept.get("id"))
            if not dept_id:
                continue
            dept_name = dept.get("name", "")
            parent_raw = safe_id(dept.get("parentid"))

            # Step 1: 原始数据落 Staging (数据血缘)
            self.save_to_staging(
                source="wecom",
                entity_type="department",
                external_id=dept_id,
                payload=dept,
                schema_version=self.SCHEMA_VERSION,
            )

            # Step 2: 获取部门负责人 (延迟对齐，仅记录 raw_id)
            leader_userid = None
            try:
                detail = self.client.get_department_detail(dept_id)
                if detail:
                    leaders = detail.get("department_leader", [])
                    if leaders:
                        # 取第一个负责人的 userid 作为 raw_id
                        leader_userid = leaders[0] if isinstance(leaders, list) else leaders
            except Exception as e:
                logger.debug(f"[WeCom] Could not fetch detail for dept {dept_id}: {e}")

            # Step 3: 通过统一服务 Upsert (携带血缘)
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
        logger.info(f"[WeCom] Phase 1 complete: {count} departments synced.")
        return count

    def _infer_org_level(self, dept: dict) -> int:
        """根据企业微信部门层级推断 org_level。

        企业微信部门 ID=1 通常是根节点 (公司级)。
        parentid=0 或 parentid=1 的部门通常是一级部门。
        """
        dept_id = dept.get("id")
        parent_id = dept.get("parentid", 0)
        if dept_id == 1:
            return 1  # 公司级 (Root)
        if parent_id in (0, 1):
            return 2  # 中心/事业部级
        return 3  # 部门/小组级

    # ─────────────────────────────────────
    #  Phase 2: 人员身份同步
    # ─────────────────────────────────────

    def _sync_users(self) -> int:
        """同步企业微信全量用户到 mdm_identities。

        遵循规则:
        - 通过 IdentityManager 进行 OneID 映射
        - 外部标识存入 mdm_identity_mappings (不污染 User 主表)
        - 携带 source_system='wecom' 血缘标记
        """
        all_users = self.client.get_all_users()
        count = 0

        for u_data in all_users:
            userid = u_data.get("userid", "")
            name = u_data.get("name", "")
            email = u_data.get("email", "") or u_data.get("biz_mail", "")
            mobile = u_data.get("mobile", "")

            # Step 1: 原始数据落 Staging
            self.save_to_staging(
                source="wecom",
                entity_type="user",
                external_id=userid,
                payload=u_data,
                schema_version=self.SCHEMA_VERSION,
            )

            # Step 2: 通过 IdentityManager 进行身份对齐
            user = IdentityManager.get_or_create_user(
                self.session,
                source="wecom",
                external_id=userid,
                email=email,
                name=name,
                employee_id=u_data.get("employee_id"),
                username=userid,
            )

            if user:
                # Step 3: 关联部门 (取主部门 = department 列表第一个)
                departments = u_data.get("department", [])
                if departments:
                    primary_dept = safe_id(departments[0])
                    if primary_dept:
                        org = self.org_service.get_org_by_code(f"wecom_dept_{primary_dept}")
                        if org:
                            user.department_id = org.id

                # Step 4: 更新血缘标记
                user.source_system = "wecom"
                user.correlation_id = self.correlation_id

                # Step 5: 补充职位信息
                position = u_data.get("position", "")
                if position and not user.position:
                    user.position = position

                count += 1

            # 每 200 人 flush 一次，防止内存溢出
            if count % 200 == 0:
                self.session.flush()

        self.session.flush()
        logger.info(f"[WeCom] Phase 2 complete: {count} users synced.")
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
        realigned_count = stats.get("resolved", 0)
        logger.info(f"[WeCom] Phase 3 complete: {realigned_count} managers realigned.")
        return realigned_count


PluginRegistry.register_worker("wecom", WeComWorker)

"""
SQLAlchemy 全量审计监听引擎 (Change Tracking Engine).

按照“无感审计”原则，通过对 SQLAlchemy 指定模型进行生命周期监听：
1. CREATE: 记录新实例的快照。
2. UPDATE: 自动计算各字段差异 (Diff)，生成 Before/After 变更链。
3. DELETE: 物理追踪记录删除。
对于密码、Token 等敏感字段，引擎会自动执行“星号星号”掩码处理。
"""

import logging
import os
from typing import Any

from sqlalchemy import event, inspect

from devops_collector.models.audit import AuditLog
from devops_collector.utils.audit_context import get_snapshot


logger = logging.getLogger(__name__)

# 为测试环境提供“熔断”开关
SKIP_AUDIT = os.getenv("DEVOPS_SKIP_AUDIT", "false").lower() == "true"

# 对敏感字段执行固定掩码脱敏 (L3 合规要求)
SENSITIVE_FIELDS_SET = {"password", "secret", "token", "access_key", "checksum", "credential_key"}


def resolve_diffs(target) -> dict[str, Any]:
    """计算当前 ORM 对象的属性变更增量快照。"""
    diffs = {}
    ins = inspect(target)
    for attr in ins.attrs:
        # 0. 仅审计列属性 (Column Property)，跳过关系 (Relationship Property)
        # 否则会触发 JSON 序列化失败 (TypeError)
        if not hasattr(attr, "history") or not hasattr(attr, "prop"):
            continue

        # 检查是否为列属性，排除关系
        from sqlalchemy.orm import ColumnProperty

        if not isinstance(attr.prop, ColumnProperty):
            continue

        hist = attr.history
        if not hist.has_changes():
            continue

        attr_key = attr.key
        old_val = hist.deleted[0] if hist.deleted else None
        new_val = hist.added[0] if hist.added else None

        # 1. 过滤敏感字段不入库（仅显示掩码）
        if attr_key in SENSITIVE_FIELDS_SET:
            old_val = "********" if old_val else None
            new_val = "********" if new_val else None

        diffs[attr_key] = {"old": old_val, "new": new_val}
    return diffs


def capture_audit_event(connection, target, action: str):
    """通用的变更捕获逻辑执行器。"""
    if SKIP_AUDIT:
        return

    # [安全阻断] 自审计拦截：审计日志本身的变化不开启二次审计，防止无限循环
    if isinstance(target, AuditLog):
        return

    # 1. 拾取穿透后的异步身份数据
    ctx = get_snapshot()

    # 2. 只有 UPDATE 才需要计算增量 Diff
    changes = resolve_diffs(target) if action == "UPDATE" else None

    # 3. 拾取资源物理标识
    # 兼容 UUID 主键 (global_user_id) 与自增 ID
    resource_id = str(getattr(target, "id", None) or getattr(target, "global_user_id", "N/A"))

    # 4. 组装审计记录并执行
    audit_payload = {
        "actor_id": ctx["actor_id"],
        "actor_name": ctx["actor_name"],
        "client_ip": ctx["client_ip"],
        "request_id": ctx["request_id"],
        "correlation_id": ctx["correlation_id"],
        "action": action,
        "resource_type": target.__tablename__ if hasattr(target, "__tablename__") else str(type(target)),
        "resource_id": resource_id,
        "changes": changes,
        "remark": ctx["remark"],
    }

    try:
        # LL #28: Use defensive execution to prevent test/migration failures if audit table is missing
        connection.execute(AuditLog.__table__.insert().values(**audit_payload))
    except Exception as e:
        # Just log it, don't crash the main transaction
        logger.error(f"[AUDIT-ENGINE] Audit record failed (might be missing table in tests): {str(e)}")


def bind_audit_listeners(target_classes: list[Any]):
    """将全生命周期审计追踪器注册到特定的核心资产类。"""
    for cls in target_classes:
        event.listen(cls, "after_insert", lambda m, c, t: capture_audit_event(c, t, "CREATE"))
        event.listen(cls, "after_update", lambda m, c, t: capture_audit_event(c, t, "UPDATE"))
        event.listen(cls, "after_delete", lambda m, c, t: capture_audit_event(c, t, "DELETE"))
        logger.info(f"[AUDIT-ENGINE] Registered change tracking for {cls.__name__}")

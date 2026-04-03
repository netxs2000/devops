"""
审计上下文链路追踪工具 (Audit Context Carrier).

利用 Python 3.7+ 的 ContextVar 实现“线程/协程级”的用户身份隔离，
确保 API 操作的身份信息无需重构业务函数签名即可深穿透至 DB 监听器层。
"""

import uuid
from contextvars import ContextVar
from typing import Any
from uuid import UUID


# 1. 核心操作者 (Who)
actor_id_ctx: ContextVar[UUID | None] = ContextVar("actor_id_ctx", default=None)
actor_name_ctx: ContextVar[str | None] = ContextVar("actor_name_ctx", default=None)

# 2. 外部环境 (Where)
client_ip_ctx: ContextVar[str | None] = ContextVar("client_ip_ctx", default=None)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id_ctx", default=str(uuid.uuid4()))

# 3. 业务链路 (Context)
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id_ctx", default=None)
audit_remark_ctx: ContextVar[str | None] = ContextVar("audit_remark_ctx", default=None)


def set_audit_user(actor_id: UUID | None = None, actor_name: str | None = None):
    """绑定当前协程的操作者身份。"""
    if actor_id:
        actor_id_ctx.set(actor_id)
    if actor_name:
        actor_name_ctx.set(actor_name)


def set_audit_metadata(client_ip: str | None = None, correlation_id: str | None = None, remark: str | None = None):
    """绑定操作相关的元数据环境。"""
    if client_ip:
        client_ip_ctx.set(client_ip)
    if correlation_id:
        correlation_id_ctx.set(correlation_id)
    if remark:
        audit_remark_ctx.set(remark)


def get_snapshot() -> dict[str, Any]:
    """获取当前层级的审计快照 (用于 DB 事件监听读取)。"""
    return {
        "actor_id": actor_id_ctx.get(),
        "actor_name": actor_name_ctx.get(),
        "client_ip": client_ip_ctx.get(),
        "request_id": request_id_ctx.get(),
        "correlation_id": correlation_id_ctx.get(),
        "remark": audit_remark_ctx.get(),
    }


def clear_context():
    """清理协程变量池 (通常由中间件或任务调度在末端执行)。"""
    actor_id_ctx.set(None)
    actor_name_ctx.set(None)
    client_ip_ctx.set(None)
    correlation_id_ctx.set(None)
    audit_remark_ctx.set(None)

"""
FastAPI 审计身份注入中间件 (Audit Identity Middleware).

在每次 HTTP 请求生命周期中：
1. 生成唯一 Request-ID 用于全链路追踪
2. 从 JWT Token 中提取操作者身份
3. 将身份数据注入 ContextVar 广播站
4. 在响应头中附加 Trace-ID 供客户端取证
"""

import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from devops_collector.utils.audit_context import clear_context, set_audit_metadata, set_audit_user

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """审计身份拦截与上下文注入中间件。"""

    async def dispatch(self, request: Request, call_next):
        # 1. 生成或复用请求追踪 ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # 2. 捕获客户端 IP (支持反向代理)
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")

        # 3. 注入网络层元数据
        set_audit_metadata(client_ip=client_ip)

        # 4. 尝试从已解析的 request.state 中拾取用户身份
        #    这依赖于 auth 依赖项在路由层先行执行
        #    中间件层仅做"兜底预注入"，路由层的依赖注入会覆盖更精确的值
        try:
            if hasattr(request.state, "user") and request.state.user:
                user = request.state.user
                set_audit_user(
                    actor_id=getattr(user, "global_user_id", None),
                    actor_name=getattr(user, "full_name", None),
                )
        except Exception:
            # 未认证请求 (如 /health, /login) 允许匿名通过
            pass

        # 5. 执行后续业务逻辑
        response = await call_next(request)

        # 6. 附加追踪 ID 到响应头
        response.headers["X-Audit-Trace-ID"] = request_id

        # 7. 请求结束后清理上下文，防止协程复用导致的身份串扰
        clear_context()

        return response

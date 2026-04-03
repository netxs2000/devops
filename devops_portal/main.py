"""GitLab 测试管理中台 - 核心 API 服务模块 (Refactored Router).

本模块作为 GitLab 社区版 (CE) 的辅助中台，提供结构化测试用例管理、
自动化质量门禁拦截、地域/部门级数据隔离以及 SSE 实时通知等核心业务。

Typical Usage:
    uvicorn devops_portal.main:app --reload --port 8000
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from devops_collector.auth import auth_router
from devops_collector.config import Config, settings
from devops_collector.core.exceptions import BusinessException
from devops_portal.dependencies import get_current_user
from devops_portal.routers import (
    admin_router,
    devex_pulse_router,
    iteration_plan_router,
    plugin_router,
    quality_router,
    security_router,
    service_desk_router,
    test_management_router,
    webhook_router,
)
from devops_portal.state import NOTIFICATION_QUEUES


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用程序生命周期。"""
    Config.http_client = httpx.AsyncClient(timeout=settings.client.timeout)
    yield
    await Config.http_client.aclose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 审计追踪中间件 (等保三级合规要求)
from devops_portal.middleware.audit import AuditMiddleware


app.add_middleware(AuditMiddleware)
app.include_router(auth_router.auth_router)
app.include_router(quality_router.router)
app.include_router(service_desk_router.router)
app.include_router(test_management_router.router)
app.include_router(iteration_plan_router.router)
app.include_router(admin_router.router)
app.include_router(devex_pulse_router.router)
app.include_router(security_router.router)
app.include_router(webhook_router.router)
app.include_router(plugin_router.router)


@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    """统一业务异常处理。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message, "code": exc.code},
    )


@app.get("/callback")
async def login_callback_compat(request: Request):
    """兼容性重定向：将旧的根路径回调重定向到 API 路由。

    修复: 之前导向 `/api/auth/gitlab/callback`，但路由注册在 `/auth` 下。将其改为转到 `/auth/gitlab/callback`，以匹配当前 API 路由并避免 404。
    """
    query_params = str(request.query_params)
    return RedirectResponse(url=f"/auth/gitlab/callback?{query_params}")


@app.get("/health")
async def health_check():
    """基础健康检查端点。"""
    return {
        "status": "ok",
        "version": settings.version if hasattr(settings, "version") else "unknown",
    }


@app.get("/notifications/stream")
async def notification_stream(current_user=Depends(get_current_user)):
    """SSE 通知流，实现实时状态更新推送。"""
    user_id = str(current_user.global_user_id)

    async def event_generator():
        '''"""TODO: Add description.

        Args:
            TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        queue = asyncio.Queue()
        if user_id not in NOTIFICATION_QUEUES:
            NOTIFICATION_QUEUES[user_id] = []
        NOTIFICATION_QUEUES[user_id].append(queue)
        try:
            # 发送一条 SSE 注释作为心跳/连接确认，不会触发前端的 onmessage 弹窗
            yield ": connected\n\n"
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            if user_id in NOTIFICATION_QUEUES:
                if queue in NOTIFICATION_QUEUES[user_id]:
                    NOTIFICATION_QUEUES[user_id].remove(queue)
                if not NOTIFICATION_QUEUES[user_id]:
                    del NOTIFICATION_QUEUES[user_id]
            raise

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Static Files Configuration


# Mount static files explicitly to /static to support frontend paths (e.g. LOGIN_PAGE in sys_core.js)
app.mount("/static", StaticFiles(directory="devops_portal/static", html=True), name="static-assets")

# Mount static files to root to serve index.html, css, js and other html pages directly (as fallback)
app.mount("/", StaticFiles(directory="devops_portal/static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104

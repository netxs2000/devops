"""Auth 认证模块。

暴露核心路由与服务接口，支持全链路命名空间对齐。
"""
from devops_collector.auth.auth_router import auth_router as router
from devops_collector.auth import auth_service as services
from devops_collector.auth.auth_database import AuthSessionLocal as SessionLocal
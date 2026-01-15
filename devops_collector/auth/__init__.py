"""Auth 认证模块。

暴露核心路由与服务接口，支持全链路命名空间对齐。
"""
from devops_collector.auth import auth_router
from devops_collector.auth import auth_service
from devops_collector.auth import auth_schema
from devops_collector.auth import auth_database
from devops_collector.auth import auth_dependency

# 别名导出，方便快速访问
auth_router_instance = auth_router.auth_router
AuthSessionLocal = auth_database.AuthSessionLocal
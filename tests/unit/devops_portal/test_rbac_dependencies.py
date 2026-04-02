from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from devops_collector.core import security
from devops_portal.dependencies import PermissionRequired, RoleRequired


@pytest.mark.anyio
async def test_role_required_logic():
    """单元测试：验证 RoleRequired 的核心校验逻辑 (Mock 依赖项)。"""
    allowed_roles = ["ADMIN"]
    guard = RoleRequired(allowed_roles)

    # RoleRequired 返回的 role_checker 签名: (current_user: User)
    # 需要构造一个带有 roles 属性的 mock user
    mock_user = MagicMock()
    mock_user.primary_email = "admin@example.com"
    mock_user.roles = [MagicMock(role_key="ADMIN")]
    mock_user.token_roles = []

    result = await guard(current_user=mock_user)
    assert result.primary_email == "admin@example.com"


@pytest.mark.anyio
async def test_role_required_forbidden():
    """单元测试：验证 RoleRequired 拒绝无权限角色。"""
    allowed_roles = ["ADMIN"]
    guard = RoleRequired(allowed_roles)

    mock_user = MagicMock()
    mock_user.primary_email = "user@example.com"
    mock_user.roles = [MagicMock(role_key="USER")]
    mock_user.token_roles = []

    with pytest.raises(HTTPException) as excinfo:
        await guard(current_user=mock_user)
    assert excinfo.value.status_code == 403


@pytest.mark.anyio
async def test_permission_required_system_admin_bypass():
    """单元测试：验证 SYSTEM_ADMIN 绕过权限点检查。"""
    guard = PermissionRequired(["SECRET_ACTION"])

    mock_user = MagicMock()
    mock_user.primary_email = "root@example.com"
    mock_user.roles = [MagicMock(role_key=security.ADMIN_ROLE_KEY)]
    mock_user.token_roles = []

    result = await guard(current_user=mock_user, db=MagicMock())
    assert result.primary_email == "root@example.com"

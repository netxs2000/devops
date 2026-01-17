import pytest
import uuid
from fastapi import HTTPException
from devops_portal.dependencies import RoleRequired, PermissionRequired
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.anyio
async def test_role_required_logic():
    """单元测试：验证 RoleRequired 的核心校验逻辑 (Mock 依赖项)。"""
    allowed_roles = ["ADMIN"]
    guard = RoleRequired(allowed_roles)
    
    # 模拟 token 解析结果
    mock_payload = {
        'sub': 'admin@example.com',
        'roles': ['ADMIN'],
        'permissions': []
    }
    
    with patch('devops_collector.auth.auth_service.auth_decode_access_token', return_value=mock_payload):
        with patch('devops_collector.auth.auth_service.auth_get_current_user') as mock_get_user:
            mock_get_user.return_value = MagicMock(primary_email='admin@example.com')
            
            # 执行校验
            result = await guard(auth_header="valid-token", db=MagicMock())
            assert result.primary_email == 'admin@example.com'

@pytest.mark.anyio
async def test_role_required_forbidden():
    """单元测试：验证 RoleRequired 拒绝无权限角色。"""
    allowed_roles = ["ADMIN"]
    guard = RoleRequired(allowed_roles)
    
    mock_payload = {
        'sub': 'user@example.com',
        'roles': ['USER'],
        'permissions': []
    }
    
    with patch('devops_collector.auth.auth_service.auth_decode_access_token', return_value=mock_payload):
        with pytest.raises(HTTPException) as excinfo:
            await guard(auth_header="user-token", db=MagicMock())
        assert excinfo.value.status_code == 403

@pytest.mark.anyio
async def test_permission_required_system_admin_bypass():
    """单元测试：验证 SYSTEM_ADMIN 绕过权限点检查。"""
    guard = PermissionRequired(["SECRET_ACTION"])
    
    # 虽然没有权限点，但是有超级管理员角色
    mock_payload = {
        'sub': 'root@example.com',
        'roles': ['SYSTEM_ADMIN'],
        'permissions': []
    }
    
    with patch('devops_collector.auth.auth_service.auth_decode_access_token', return_value=mock_payload):
        with patch('devops_collector.auth.auth_service.auth_get_current_user') as mock_get_user:
            mock_get_user.return_value = MagicMock(primary_email='root@example.com')
            
            result = await guard(auth_header="root-token", db=MagicMock())
            assert result.primary_email == 'root@example.com'

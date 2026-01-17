import pytest
from fastapi.testclient import TestClient
from devops_collector.auth import auth_service
from devops_collector.models.base_models import User, Role, Permission, UserRole, RolePermission
import uuid

def create_test_token(email, user_id, roles=None, permissions=None):
    """Helper to create a JWT for testing."""
    token_data = {
        'sub': email,
        'user_id': str(user_id),
        'roles': roles or [],
        'permissions': permissions or []
    }
    return auth_service.auth_create_access_token(token_data)

def test_rbac_unauthorized_access(client, db_session):
    """验证普通用户无法访问需要特定权限的接口 (越权访问拦截)。"""
    # 1. 创建一个没有任何特殊角色的普通用户
    uid = uuid.uuid4()
    user = User(
        global_user_id=uid,
        primary_email="normie@example.com",
        username="normie",
        full_name="Normal User",
        is_active=True,
        is_current=True
    )
    db_session.add(user)
    db_session.commit()
    
    # 生成无权限 Token
    token = create_test_token(user.primary_email, user.global_user_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 尝试访问需要 USER:VIEW 的用户列表接口
    resp = client.get("/admin/users", headers=headers)
    assert resp.status_code == 403
    assert "Missing permissions" in resp.json()["detail"]
    
    # 3. 尝试访问需要 SYSTEM_ADMIN 的身份映射创建接口
    resp = client.post("/admin/identity-mappings", json={}, headers=headers)
    assert resp.status_code == 403
    assert "Required roles" in resp.json()["detail"]

def test_rbac_authorized_access_by_permission(client, db_session):
    """验证拥有特定权限的用户可以访问受限接口。"""
    uid = uuid.uuid4()
    user = User(
        global_user_id=uid,
        primary_email="viewer@example.com",
        username="viewer",
        full_name="Viewer User",
        is_active=True,
        is_current=True
    )
    db_session.add(user)
    db_session.commit()
    
    # 模拟拥有 USER:VIEW 权限
    token = create_test_token(user.primary_email, user.global_user_id, permissions=["USER:VIEW"])
    headers = {"Authorization": f"Bearer {token}"}
    
    # 访问响应
    resp = client.get("/admin/users", headers=headers)
    # 因为 DB 中有用户了，即使空也应该是 200
    assert resp.status_code == 200

def test_rbac_system_admin_override(client, db_session):
    """验证 SYSTEM_ADMIN 角色可以越过所有权限检查。"""
    uid = uuid.uuid4()
    user = User(
        global_user_id=uid,
        primary_email="admin@example.com",
        username="admin",
        full_name="Admin User",
        is_active=True,
        is_current=True
    )
    db_session.add(user)
    db_session.commit()
    
    # 即使没有任何权限点，只有 SYSTEM_ADMIN 角色也应该能通过
    token = create_test_token(user.primary_email, user.global_user_id, roles=["SYSTEM_ADMIN"])
    headers = {"Authorization": f"Bearer {token}"}
    
    # 访问需要权限点的接口
    resp = client.get("/admin/users", headers=headers)
    assert resp.status_code == 200
    
    # 访问需要特定角色的接口 (IDENTITY MAPPING)
    payload = {
        "global_user_id": str(uid),
        "source_system": "test",
        "external_user_id": "EXT1",
        "external_username": "tester"
    }
    resp = client.post("/admin/identity-mappings", json=payload, headers=headers)
    assert resp.status_code == 200

def test_rbac_write_operations_denied(client, db_session):
    """验证普通用户尝试执行管理员写操作被拦截。"""
    uid = uuid.uuid4()
    user = User(global_user_id=uid, primary_email="normie2@example.com", is_active=True)
    db_session.add(user)
    db_session.commit()
    
    token = create_test_token(user.primary_email, user.global_user_id, roles=["USER"])
    headers = {"Authorization": f"Bearer {token}"}
    
    # 尝试创建团队
    resp = client.post("/admin/teams", json={"name": "Evil Team", "team_code": "EVIL"}, headers=headers)
    assert resp.status_code == 403
    
    # 尝试创建项目
    resp = client.post("/admin/mdm-projects", json={"project_id": "P1_EVIL", "project_name": "P1"}, headers=headers)
    assert resp.status_code == 403

def test_rbac_team_management_flow(client, db_session):
    """验证管理员完整的团队管理提权流程并校验数据一致性 (N+1 优化校验)。"""
    uid = uuid.uuid4()
    user = User(
        global_user_id=uid, 
        primary_email="boss@example.com", 
        full_name="Big Boss",
        username="boss",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    
    # 仅给予 SYSTEM_ADMIN 角色
    token = create_test_token(user.primary_email, user.global_user_id, roles=["SYSTEM_ADMIN"])
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. 创建团队
    team_data = {"name": "Test Team Alpha", "team_code": "ALPHA", "description": "RBAC Test"}
    resp = client.post("/admin/teams", json=team_data, headers=headers)
    assert resp.status_code == 200
    team_id = resp.json()["id"]
    
    # 2. 添加成员
    member_data = {"user_id": str(uid), "role_code": "LEAD", "allocation_ratio": 1.0}
    resp = client.post(f"/admin/teams/{team_id}/members", json=member_data, headers=headers)
    assert resp.status_code == 200
    
    # 3. 验证列表显示 (核心验证：确保 Eager Loading 下字段依然准确)
    resp = client.get("/admin/teams", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(t["id"] == team_id for t in data)
    target_team = next(t for t in data if t["id"] == team_id)
    assert len(target_team["members"]) == 1
    # 重要断言：验证成员关联的用户姓名是否被正确加载 (joinedload 验证)
    assert target_team["members"][0]["full_name"] == "Big Boss"

def test_rbac_token_expired_or_invalid(client):
    """验证无效或过期的 Token 被拦截。"""
    headers = {"Authorization": "Bearer invalid-token"}
    resp = client.get("/admin/users", headers=headers)
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]

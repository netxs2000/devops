import pytest
import uuid
from devops_collector.models.base_models import User, IdentityMapping
from devops_collector.auth import auth_service

def create_test_token(email, user_id, roles=None, permissions=None):
    """Helper to create a JWT for testing."""
    token_data = {
        'sub': email,
        'user_id': str(user_id),
        'roles': roles or [],
        'permissions': permissions or []
    }
    return auth_service.auth_create_access_token(token_data)

def test_list_all_users_for_admin(client, db_session):
    """集成测试：验证管理员用户审批清单及统计。"""
    # 模拟一个待审批用户
    u1 = User(
        global_user_id=uuid.uuid4(),
        primary_email="pending@example.com",
        full_name="Pending User",
        is_active=False,
        is_survivor=True, # survivor=True and active=False means pending
        is_current=True
    )
    # 模拟一个已批准用户
    u2 = User(
        global_user_id=uuid.uuid4(),
        primary_email="approved@example.com",
        full_name="Approved User",
        is_active=True,
        is_survivor=True,
        is_current=True
    )
    # 创建管理员用户
    admin_id = uuid.uuid4()
    admin = User(
        global_user_id=admin_id,
        primary_email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_current=True
    )
    db_session.add_all([u1, u2, admin])
    db_session.commit()
    
    # 赋予 USER:MANAGE 权限
    token = create_test_token("admin@example.com", admin_id, permissions=["USER:MANAGE"])
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/service-desk/admin/all-users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # 验证统计数据
    assert data["stats"]["pending"] >= 1
    assert data["stats"]["approved"] >= 1
    
    # 验证列表中包含待处理用户
    emails = [u["email"] for u in data["users"]]
    assert "pending@example.com" in emails

def test_approve_user_application(client, db_session):
    """集成测试：验证用户审批通过及身份自动绑定流程。"""
    user_id = uuid.uuid4()
    user = User(
        global_user_id=user_id,
        primary_email="to_approve@example.com",
        full_name="To Approve",
        is_active=False,
        is_survivor=True,
        is_current=True
    )
    # 创建管理员用户
    admin_id = uuid.uuid4()
    admin = User(
        global_user_id=admin_id,
        primary_email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_current=True
    )
    db_session.add_all([user, admin])
    db_session.commit()
    
    token = create_test_token("admin@example.com", admin_id, permissions=["USER:MANAGE"])
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "email": "to_approve@example.com",
        "approved": True,
        "gitlab_user_id": "GL-123"
    }
    
    response = client.post("/service-desk/admin/approve-user", params=payload, headers=headers)
    assert response.status_code == 200
    
    # 验证数据库状态
    db_session.refresh(user)
    assert user.is_active is True
    
    # 验证身份映射
    mapping = db_session.query(IdentityMapping).filter_by(
        global_user_id=user_id, 
        source_system='gitlab'
    ).first()
    assert mapping is not None
    assert mapping.external_user_id == "GL-123"

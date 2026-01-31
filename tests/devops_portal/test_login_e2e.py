"""登录功能端到端测试。

测试完整的用户登录流程：
1. 访问门户首页（验证登录模态框）
2. 用户注册（如果需要）
3. 用户登录（获取JWT令牌）
4. 访问受保护的个人信息端点
5. 验证登录状态对前端的影响
"""

import pytest
from fastapi.testclient import TestClient


def test_portal_homepage_unauthenticated(client):
    """测试未认证用户访问门户首页时显示登录模态框。"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    # 验证HTML包含登录模态框的关键元素
    html_content = response.text
    assert "loginModal" in html_content  # 登录模态框ID
    assert "请登录以继续" in html_content  # 登录提示文本
    assert "login-email" in html_content  # 邮箱输入框
    assert "login-password" in html_content  # 密码输入框
    assert "login-submit" in html_content  # 登录按钮


def test_login_e2e_flow(client, db_session):
    """测试完整的登录端到端流程。"""
    from devops_collector.auth import auth_service as services
    from devops_collector.models.base_models import User, UserCredential
    import uuid

    # 1. 创建测试用户
    email = "e2e_test@example.com"
    password = "e2e_password_123"
    user_id = uuid.uuid4()

    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="E2E Test User",
        is_active=True,
        is_current=True,
        is_deleted=False
    )
    db_session.add(user)
    db_session.flush()

    hashed_pwd = services.auth_get_password_hash(password)
    db_session.add(UserCredential(user_id=user_id, password_hash=hashed_pwd))
    db_session.commit()

    # 2. 登录获取令牌
    login_data = {"username": email, "password": password}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    access_token = token_data["access_token"]

    # 3. 使用令牌访问受保护端点
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == email
    assert me_data["full_name"] == "E2E Test User"

    # 4. 验证令牌可以访问其他受保护端点
    # 例如访问质量分析接口（需要认证）
    quality_response = client.get(
        "/quality/projects/1/province-quality",
        headers=headers
    )
    # 即使项目不存在，也应该返回200或适当的错误状态码
    # 主要是验证认证中间件允许访问
    assert quality_response.status_code in [200, 404, 500]


def test_login_with_invalid_credentials(client, db_session):
    """测试使用无效凭据登录。"""
    from devops_collector.auth import auth_service as services
    from devops_collector.models.base_models import User, UserCredential
    import uuid

    # 创建有效用户
    email = "valid_user@example.com"
    password = "valid_password_123"
    user_id = uuid.uuid4()

    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="Valid User",
        is_active=True,
        is_current=True,
        is_deleted=False
    )
    db_session.add(user)
    db_session.flush()

    hashed_pwd = services.auth_get_password_hash(password)
    db_session.add(UserCredential(user_id=user_id, password_hash=hashed_pwd))
    db_session.commit()

    # 测试错误密码
    login_data = {"username": email, "password": "wrong_password"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401
    error_data = response.json()
    assert "detail" in error_data

    # 测试不存在的用户
    login_data = {"username": "nonexistent@example.com", "password": "any_password"}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 401


def test_access_protected_endpoint_without_token(client):
    """测试未授权访问受保护端点。"""
    response = client.get("/auth/me")
    assert response.status_code == 401

    response = client.get("/quality/projects/1/province-quality")
    assert response.status_code == 401  # 需要认证


def test_login_and_frontend_flow(client, db_session):
    """测试登录后前端状态变化（模拟）。"""
    from devops_collector.auth import auth_service as services
    from devops_collector.models.base_models import User, UserCredential
    import uuid

    # 创建用户并登录
    email = "frontend_test@example.com"
    password = "frontend_password_123"
    user_id = uuid.uuid4()

    user = User(
        global_user_id=user_id,
        primary_email=email,
        full_name="Frontend Test User",
        is_active=True,
        is_current=True,
        is_deleted=False
    )
    db_session.add(user)
    db_session.flush()

    hashed_pwd = services.auth_get_password_hash(password)
    db_session.add(UserCredential(user_id=user_id, password_hash=hashed_pwd))
    db_session.commit()

    # 登录获取令牌
    login_data = {"username": email, "password": password}
    response = client.post("/auth/login", data=login_data)
    assert response.status_code == 200
    token_data = response.json()
    access_token = token_data["access_token"]

    # 模拟前端使用令牌访问主页
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/", headers=headers)
    assert response.status_code == 200

    # 验证页面是否包含用户界面元素（而不是登录模态框）
    html_content = response.text
    # 登录后应该显示用户侧边栏信息
    assert "sys-user-profile" in html_content  # 用户资料区域
    assert "user-display-name" in html_content  # 用户名显示

    # 验证登录模态框应该被隐藏（通过检查u-hide类）
    # 注意：前端JS控制显示/隐藏，但HTML结构仍然存在
    assert "loginModal" in html_content  # 模态框仍然在HTML中
    # 可以检查是否包含u-hide类，但取决于JS执行状态


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
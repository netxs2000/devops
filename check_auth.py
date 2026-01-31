#!/usr/bin/env python3
"""诊断脚本：检查认证系统和前端功能"""

import sys
import requests
import json

def test_api_endpoints():
    """测试API端点"""
    base_url = "http://localhost:8000"

    print("1. 测试主页静态文件...")
    try:
        resp = requests.get(f"{base_url}/", timeout=5)
        print(f"   状态码: {resp.status_code}")
        print(f"   内容类型: {resp.headers.get('content-type')}")
        print(f"   内容长度: {len(resp.text)} 字节")

        # 检查关键HTML元素
        html = resp.text
        checks = [
            ("loginModal", "登录模态框"),
            ("login-email", "邮箱输入框"),
            ("login-password", "密码输入框"),
            ("login-submit", "登录按钮"),
            ("sys-sidebar", "侧边栏"),
            ("sys-user-profile", "用户资料区域")
        ]

        for elem, desc in checks:
            if elem in html:
                print(f"   ✓ 找到: {desc} ({elem})")
            else:
                print(f"   ✗ 未找到: {desc} ({elem})")

    except Exception as e:
        print(f"   错误: {e}")

    print("\n2. 测试未授权访问 /auth/me...")
    try:
        resp = requests.get(f"{base_url}/auth/me", timeout=5)
        print(f"   状态码: {resp.status_code}")
        if resp.status_code == 401:
            print("   ✓ 正确返回401未授权")
        else:
            print(f"   响应: {resp.text[:200]}")
    except Exception as e:
        print(f"   错误: {e}")

    print("\n3. 测试登录API...")
    try:
        # 使用初始化脚本中的默认管理员账号
        login_data = {
            "username": "admin@tjhq.com",
            "password": "admin_password_123!"
        }
        resp = requests.post(
            f"{base_url}/auth/login",
            data=login_data,
            timeout=5
        )
        print(f"   状态码: {resp.status_code}")

        if resp.status_code == 200:
            token_data = resp.json()
            print(f"   ✓ 登录成功")
            print(f"   令牌类型: {token_data.get('token_type')}")
            print(f"   访问令牌长度: {len(token_data.get('access_token', ''))} 字符")

            # 用令牌测试 /auth/me
            print("\n4. 测试使用令牌访问 /auth/me...")
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            resp = requests.get(f"{base_url}/auth/me", headers=headers, timeout=5)
            print(f"   状态码: {resp.status_code}")
            if resp.status_code == 200:
                user_data = resp.json()
                print(f"   ✓ 成功获取用户信息")
                print(f"   邮箱: {user_data.get('email')}")
                print(f"   姓名: {user_data.get('full_name')}")
                print(f"   角色: {user_data.get('roles', [])}")
                print(f"   权限: {len(user_data.get('permissions', []))} 个权限")
                print(f"   数据范围: {user_data.get('data_scope')}")
            else:
                print(f"   错误: {resp.text[:200]}")
        else:
            print(f"   ✗ 登录失败")
            print(f"   响应: {resp.text[:200]}")

    except Exception as e:
        print(f"   错误: {e}")

    print("\n5. 测试CSS和JS静态文件...")
    static_files = ["css/main.css", "js/modules/sys_core.js"]
    for file_path in static_files:
        try:
            resp = requests.get(f"{base_url}/{file_path}", timeout=5)
            print(f"   {file_path}: 状态码 {resp.status_code}, 长度 {len(resp.text)} 字节")
        except Exception as e:
            print(f"   {file_path}: 错误 {e}")

def check_database():
    """检查数据库状态"""
    print("\n6. 检查数据库...")
    try:
        import os
        import psycopg2
        from urllib.parse import urlparse

        # 从环境变量获取数据库连接
        db_url = os.environ.get("DB_URI", "postgresql://devops:devops123@db/devops")

        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # 检查用户表
        cur.execute("SELECT COUNT(*) FROM mdm_identities WHERE is_current = TRUE AND is_deleted = FALSE")
        user_count = cur.fetchone()[0]
        print(f"   当前有效用户数: {user_count}")

        # 检查超级管理员
        cur.execute("""
            SELECT u.primary_email, u.full_name, r.role_key
            FROM mdm_identities u
            LEFT JOIN sys_user_role ur ON u.global_user_id = ur.user_id
            LEFT JOIN sys_role r ON ur.role_id = r.id
            WHERE u.primary_email = 'admin@tjhq.com' AND u.is_current = TRUE
        """)
        admin = cur.fetchone()
        if admin:
            print(f"   超级管理员: {admin[0]} ({admin[1]})")
            print(f"   角色: {admin[2] if admin[2] else '无角色'}")
        else:
            print("   ✗ 未找到超级管理员")

        # 检查角色
        cur.execute("SELECT role_key, role_name, data_scope FROM sys_role WHERE del_flag = FALSE ORDER BY id")
        roles = cur.fetchall()
        print(f"   系统角色数: {len(roles)}")
        for role in roles[:5]:  # 显示前5个
            print(f"     - {role[0]}: {role[1]} (数据范围: {role[2]})")

        # 检查菜单
        cur.execute("SELECT COUNT(*) FROM sys_menu WHERE status = TRUE")
        menu_count = cur.fetchone()[0]
        print(f"   可用菜单数: {menu_count}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"   数据库检查错误: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("DevOps Portal 认证系统诊断")
    print("=" * 60)

    test_api_endpoints()
    check_database()

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

    print("\n建议:")
    print("1. 确保使用 HTTP (不是 HTTPS) 访问: http://127.0.0.1:8000")
    print("2. 清除浏览器缓存和 localStorage")
    print("3. 检查浏览器开发者工具 (F12) 的 Console 和 Network 标签")
    print("4. 如果仍然有问题，尝试使用隐身模式访问")
    print("5. 默认管理员账号: admin@tjhq.com / admin_password_123!")
import sys
import os
import httpx
import asyncio
from typing import Dict, Any

# 将当前目录添加到系统路径
sys.path.insert(0, os.getcwd())

async def diagnose():
    """系统综合诊断脚本。
    
    检查项目：
    1. API 连通性 (Health Check)
    2. 数据库连接 & 基础数据 (Identity Check)
    3. GitLab OAuth 配置校验
    """
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("DevOps Platform 系统综合诊断")
    print("=" * 60)

    # 1. 检查 API 连通性
    print("\n[1/3] 检查 API 连通性...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{base_url}/health", timeout=5)
            if resp.status_code == 200:
                print(f"   ✓ API 服务运行正常: {resp.json()}")
            else:
                print(f"   ✗ API 服务返回异常状态码: {resp.status_code}")
        except Exception as e:
            print(f"   ✗ 无法连接到 API 服务 (请确保已运行 make up): {e}")

    # 2. 检查数据库和管理员账户
    print("\n[2/3] 检查数据库与角色...")
    try:
        from devops_collector.auth.auth_database import AuthSessionLocal
        from devops_collector.models.base_models import User, SysRole
        
        db = AuthSessionLocal()
        user_count = db.query(User).filter_by(is_current=True).count()
        role_count = db.query(SysRole).filter_by(del_flag=False).count()
        admin_user = db.query(User).filter_by(primary_email="admin@tjhq.com", is_current=True).first()
        
        print(f"   ✓ 数据库连接正常")
        print(f"   ✓ 当前用户数: {user_count}")
        print(f"   ✓ 系统角色数: {role_count}")
        
        if admin_user:
            print(f"   ✓ 管理员账户存在: {admin_user.full_name} (Active: {admin_user.is_active})")
        else:
            print(f"   ⚠ 管理员账户 (admin@tjhq.com) 未找到")
        db.close()
    except Exception as e:
        print(f"   ✗ 数据库检查失败: {e}")

    # 3. 检查 GitLab 配置
    print("\n[3/3] 检查 GitLab OAuth 配置...")
    try:
        from devops_collector.config import settings
        gl = settings.gitlab
        print(f"   GitLab URL: {gl.url}")
        if gl.client_id and gl.client_secret and gl.redirect_uri:
            print(f"   ✓ OAuth 配置项已填写 (ID: {gl.client_id[:5]}***)")
        else:
            print(f"   ⚠ OAuth 配置不完整，GitLab 登录功能将不可用")
        
        if not gl.verify_ssl:
            print(f"   ⚠ 已禁用 SSL 验证 (verify_ssl=False)")
    except Exception as e:
        print(f"   ✗ 配置检查失败: {e}")

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(diagnose())

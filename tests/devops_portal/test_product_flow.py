import pytest
import uuid
from devops_collector.models.base_models import User, Organization, ProjectMaster, Product # Use direct imports
from devops_portal.dependencies import get_current_user
from devops_collector.auth import auth_service
from devops_portal.main import app
# Import ProjectProductRelation but use it via db queries if needed, or rely on router response

def create_test_token(email, user_id, roles=None, permissions=None):
    """Helper to create a JWT for testing."""
    token_data = {
        'sub': email,
        'user_id': str(user_id),
        'roles': roles or [],
        'permissions': permissions or []
    }
    return auth_service.auth_create_access_token(token_data)

def test_product_management_flow(client, db_session):
    """集成测试：验证产品创建与项目关联的完整流程。"""
    
    # 创建系统管理员
    admin_id = uuid.uuid4()
    admin = User(
        global_user_id=admin_id,
        primary_email="admin@example.com",
        full_name="Admin User",
        is_active=True,
        is_current=True
    )
    db_session.add(admin)
    
    # 创建 Organization (必须有 org_id)
    org = Organization(org_id="ORG-001", org_name="Test Organization")
    db_session.add(org)
    
    db_session.commit()
    
    token = create_test_token("admin@example.com", admin_id, roles=["SYSTEM_ADMIN"])
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. 创建产品
    product_data = {
        "product_id": "P-BIZ-01",
        "product_code": "BIZ_CORE",
        "product_name": "Business Core Platform",
        "product_description": "Core platform for business services",
        "category": "Core",
        "version_schema": "semver"
    }
    
    response = client.post("/admin/products", json=product_data, headers=headers)
    assert response.status_code == 200, f"Create product failed: {response.text}"
    assert response.json()["product_id"] == "P-BIZ-01"
    
    # 2. 准备项目 (关联Org)
    project = ProjectMaster(
        project_id="MDM-PROJ-01", 
        project_name="MDM Project 1",
        org_id="ORG-001" 
    )
    db_session.add(project)
    db_session.commit()
    
    # 3. 关联产品到项目
    relation_data = {
        "project_id": "MDM-PROJ-01",
        "product_id": "P-BIZ-01",
        "relation_type": "PRIMARY",
        "allocation_ratio": 1.0
    }
    
    response = client.post("/admin/link-product", json=relation_data, headers=headers)
    assert response.status_code == 200, f"Link product failed: {response.text}"
    assert response.json()["relation_type"] == "PRIMARY"
    
    # 4. 验证列表接口返回值 (N+1 优化校验)
    
    response = client.get("/admin/mdm-projects", headers=headers)
    assert response.status_code == 200, f"List projects failed: {response.text}"
    data = response.json()
    
    target_proj = next((p for p in data if p["project_id"] == "MDM-PROJ-01"), None)
    assert target_proj is not None
    
    # 验证产品列表存在
    assert "products" in target_proj
    assert len(target_proj["products"]) > 0
    assert target_proj["products"][0]["product_id"] == "P-BIZ-01"

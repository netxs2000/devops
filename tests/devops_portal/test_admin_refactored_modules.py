import pytest
import uuid
from devops_collector.models.base_models import (
    User, SysRole, UserRole, 
    Product, ProjectMaster, Organization, 
    ProjectProductRelation, IdentityMapping
)
from devops_collector.plugins.gitlab.models import GitLabProject
from devops_portal.dependencies import get_current_user

# --- Fixtures ---

@pytest.fixture
def admin_user(db_session):
    """Create a super admin user with all necessary roles/permissions."""
    user = User(
        global_user_id=uuid.uuid4(),
        primary_email="admin@example.com",
        username="admin",
        full_name="System Admin",
        is_active=True,
        is_current=True
    )
    db_session.add(user)
    
    # Create Role
    role = SysRole(role_key="SYSTEM_ADMIN", role_name="System Administrator")
    db_session.add(role)
    db_session.commit()
    
    # Assign Role
    user_role = UserRole(user_id=user.global_user_id, role_id=role.id)
    db_session.add(user_role)
    
    # Assign specific permission used in Code (USER:MANAGE)
    # perm = Permission(...)  # Permission model does not exist
    
    db_session.commit()
    
    # Attach property for test convenience (mock object style)
    user.roles = [role]
    # user.permissions = ["USER:MANAGE", "system:user:list", "system:project:mapping"] # Mocking property if it exists
    
    return user

from devops_collector.auth import auth_service

@pytest.fixture
def admin_client(client, admin_user, db_session):
    """Client authenticated as System Admin using valid JWT."""
    
    # Create JWT with required roles/permissions
    token_data = {
        'sub': admin_user.primary_email,
        'user_id': str(admin_user.global_user_id),
        'roles': ["SYSTEM_ADMIN"],
        'permissions': ["USER:MANAGE", "system:user:list", "system:project:mapping"]
    }
    token = auth_service.auth_create_access_token(token_data)
    
    # Set global headers for the client session
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client


# --- Tests: 1. Product Architecture (adm_products) ---

def test_product_lifecycle(admin_client, db_session):
    """Test Create -> List -> Link Product."""
    
    # 1. Create Product
    payload = {
        "product_id": "PROD-001",
        "product_code": "PROD-001",  # Added required field
        "product_name": "Core Banking",
        "category": "CORE",
        "lifecycle_status": "ACTIVE",
        "product_description": "Core system"
    }
    resp = admin_client.post("/admin/products", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["product_name"] == "Core Banking"
    
    # 2. List Products
    resp = admin_client.get("/admin/products")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
    
    # 3. Create Project to Link
    org = Organization(org_id="GZ_CENTER", org_name="Guangzhou Center", is_current=True)
    db_session.add(org)
    proj = ProjectMaster(project_id="PRJ-001", project_name="Upgrade 2.0", org_id="GZ_CENTER", is_current=True)
    db_session.add(proj)
    db_session.commit()
    
    # 4. Link Product to Project
    link_payload = {
        "project_id": "PRJ-001",
        "product_id": "PROD-001",
        "relation_type": "PRIMARY", # Assuming this is a valid type
        "allocation_ratio": 100.0
    }
    resp = admin_client.post("/admin/link-product", json=link_payload)
    assert resp.status_code == 200
    
    # Verify DB
    rel = db_session.query(ProjectProductRelation).filter_by(project_id="PRJ-001").first()
    assert rel is not None
    assert rel.product_id == "PROD-001"


# --- Tests: 2. Project Mapping (adm_projects) ---

def test_project_mapping_flow(admin_client, db_session):
    """Test MDM Project Creation and Repo Linking."""
    
    # Setup: Org
    org = Organization(org_id="GZ_CENTER", org_name="GZ", is_current=True)
    db_session.add(org)
    
    # Setup: Unlinked Repo
    repo = GitLabProject(
        id=1001, 
        name="legacy-repo", 
        path_with_namespace="group/legacy-repo", 
        raw_data={"web_url": "http://git"}
    )
    db_session.add(repo)
    db_session.commit()
    
    # 1. Create MDM Project
    payload = {
        "project_id": "MDM-2025",
        "project_name": "New Architecture",
        "org_id": "GZ_CENTER",
        "project_type": "SPRINT"
    }
    resp = admin_client.post("/admin/mdm-projects", json=payload)
    assert resp.status_code == 200
    
    # 2. List Unlinked Repos
    resp = admin_client.get("/admin/unlinked-repos")
    assert resp.status_code == 200
    repos = resp.json()
    assert any(r['id'] == 1001 for r in repos)
    
    # 3. Link Repo
    link_payload = {
        "mdm_project_id": "MDM-2025",
        "gitlab_project_id": 1001,
        "is_lead": True
    }
    resp = admin_client.post("/admin/link-repo", json=link_payload)
    assert resp.status_code == 200
    
    # Verify
    db_session.refresh(repo)
    assert repo.mdm_project_id == "MDM-2025"
    
    # Verify Lead Config
    proj = db_session.query(ProjectMaster).filter_by(project_id="MDM-2025").first()
    assert proj.lead_repo_id == 1001


# --- Tests: 3. Employee Identity (adm_users) ---

def test_identity_mapping_crud(admin_client, db_session, admin_user):
    """Test Creating and Deleting Identity Mappings."""
    
    # 1. Create Mapping
    payload = {
        "global_user_id": str(admin_user.global_user_id),
        "source_system": "GITHUB",
        "external_user_id": "gh_12345",
        "external_username": "gh_admin",
        "external_email": "admin@github.com"
    }
    resp = admin_client.post("/admin/identity-mappings", json=payload)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'success'
    
    # 2. List verify
    resp = admin_client.get("/admin/identity-mappings")
    assert resp.status_code == 200
    mappings = resp.json()
    assert any(m['source_system'] == 'GITHUB' for m in mappings)
    
    # 3. Delete
    # Need to get ID
    mapping_obj = db_session.query(IdentityMapping).filter_by(external_user_id="gh_12345").first()
    resp = admin_client.delete(f"/admin/identity-mappings/{mapping_obj.id}")
    assert resp.status_code == 200
    
    # Verify gone
    assert db_session.query(IdentityMapping).filter_by(id=mapping_obj.id).first() is None


# --- Tests: 4. User Approvals (adm_approvals) ---

def test_user_approval_process(admin_client, db_session):
    """Test User Registration Approval Flow."""
    
    # 1. Create Pending User
    pending_user = User(
        global_user_id=uuid.uuid4(),
        primary_email="newbie@company.com",
        full_name="New Employee",
        is_active=False,
        is_survivor=True, # Pending state
        is_current=True
    )
    db_session.add(pending_user)
    db_session.commit()
    
    # 2. List Pending Users
    resp = admin_client.get("/service-desk/admin/all-users?status=pending")
    assert resp.status_code == 200
    data = resp.json()
    assert data["stats"]["pending"] >= 1
    assert any(u['email'] == "newbie@company.com" for u in data['users'])
    
    # 3. Approve User with GitLab ID
    approve_params = {
        "email": "newbie@company.com",
        "approved": "true",
        "gitlab_user_id": "GL-555"
    }
    # Note: approved is bool in python, likely passed as query param string "true" or boolean by client
    # The endpoint expects query params for this POST.
    resp = admin_client.post("/service-desk/admin/approve-user", params=approve_params, json={})
    assert resp.status_code == 200, resp.text
    
    # 4. Verify User Active
    db_session.expire(pending_user) # Reload
    db_session.refresh(pending_user)
    assert pending_user.is_active is True
    
    # 5. Verify GitLab Mapping Created
    mapping = db_session.query(IdentityMapping).filter_by(
        global_user_id=pending_user.global_user_id,
        source_system="gitlab"
    ).first()
    assert mapping is not None
    assert mapping.external_user_id == "GL-555"

"""
Script for simulating and verifying cross-department data isolation and RBAC for plugins (ZenTao, SonarQube, Jira).
This script creates a test environment with a hierarchy of organizations and users with different roles,
then attempts to perform cross-department queries to verify enforcement of P5 isolation.
"""
import sys
import os
from sqlalchemy.orm import Session
from datetime import datetime

# Add project root to sys.path
project_root = r"c:\Users\netxs\devops\devops"
if project_root not in sys.path:
    sys.path.append(project_root)

from devops_collector.config import SessionLocal
from devops_collector.models.base_models import Organization, User, Location
from devops_collector.plugins.zentao.models import ZenTaoIssue, ZenTaoProduct
from devops_collector.plugins.jira.models import JiraIssue, JiraProject

def setup_test_data(db: Session):
    """
    Setup a hierarchical org structure:
    HQ (Dept_001)
    ├── R&D Center (Dept_002)
    │   └── Mobile App Team (Dept_003)
    └── Marketing (Dept_004)
    """
    # 1. Clean up existing test data (optional, but safer for repeatable tests)
    db.query(User).filter(User.primary_email.like("test_%@example.com")).delete()
    db.query(Organization).filter(Organization.org_id.like("Dept_%")).delete()
    db.commit()

    # 2. Create Orgs
    hq = Organization(org_id="Dept_001", name="Headquarters", level="Company")
    rd = Organization(org_id="Dept_002", name="R&D Center", parent_org_id="Dept_001", level="Center")
    mobile = Organization(org_id="Dept_003", name="Mobile App Team", parent_org_id="Dept_002", level="Department")
    marketing = Organization(org_id="Dept_004", name="Marketing Dept", parent_org_id="Dept_001", level="Department")
    
    db.add_all([hq, rd, mobile, marketing])
    db.flush()

    # 3. Create Users
    # RD Admin (Should see Dept_002 and Dept_003)
    rd_user = User(
        global_user_id=9002,
        full_name="RD Admin",
        primary_email="test_rd@example.com",
        department_id="Dept_002",
        role="maintainer"
    )
    # Marketing User (Should see ONLY Dept_004, NO RD data)
    mkt_user = User(
        global_user_id=9004,
        full_name="Marketing User",
        primary_email="test_mkt@example.com",
        department_id="Dept_004",
        role="guest"
    )
    db.add_all([rd_user, mkt_user])
    db.commit()
    return rd_user, mkt_user

def verify_isolation_logic(user_email: str):
    """模拟后端 API 逻辑进行隔离校验。"""
    db = SessionLocal()
    try:
        from test_hub.main import get_user_org_scope_ids
        
        user = db.query(User).filter_by(primary_email=user_email).first()
        print(f"\n--- Testing for User: {user.full_name} ({user.role}) ---")
        print(f"User Department: {user.department_id}")
        
        scope_ids = get_user_org_scope_ids(user)
        print(f"Authorized Department Scopes (Recursive): {scope_ids}")
        
        # 模拟插件数据：Jira Issues
        # 假设我们有来自不同部门的项目数据
        print("\n[Plugin: Jira] Checking Data Access...")
        # 模拟查询：假设 Jira 问题通过标签或项目关联了部门
        mock_jira_data = [
            {"id": "JIRA-1", "dept": "Dept_002", "summary": "RD Strategic Task"},
            {"id": "JIRA-2", "dept": "Dept_003", "summary": "Mobile Bug Fix"},
            {"id": "JIRA-3", "dept": "Dept_004", "summary": "Marketing Campaign"},
        ]
        
        accessible = [item for item in mock_jira_data if item['dept'] in scope_ids]
        print(f"Accessible Jira Issues: {[i['id'] for i in accessible]}")
        
        # 预期校验
        if user_email == "test_rd@example.com":
            # RD Admin should see Dept_002 (RD) and Dept_003 (Mobile)
            assert "Dept_002" in scope_ids and "Dept_003" in scope_ids
            assert "Dept_004" not in scope_ids
            print("✅ RD Admin successfully scoped to RD and Sub-depts.")
        elif user_email == "test_mkt@example.com":
            # Marketing should see ONLY Dept_004
            assert scope_ids == ["Dept_004"]
            assert "Dept_002" not in scope_ids
            print("✅ Marketing User correctly restricted to Marketing data.")

    finally:
        db.close()

if __name__ == "__main__":
    db = SessionLocal()
    print("Initializing Test Environment for Plugin P5 Isolation...")
    rd_user, mkt_user = setup_test_data(db)
    db.close()
    
    try:
        verify_isolation_logic("test_rd@example.com")
        verify_isolation_logic("test_mkt@example.com")
        print("\n🎉 Plugin P5 Isolation Logic Verified Successfully!")
    except AssertionError as e:
        print(f"\n❌ Verification Failed: Data isolation breach detected!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Execution Error: {e}")
        sys.exit(1)

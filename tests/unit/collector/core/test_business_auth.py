"""业务关联授权单元测试 (Unit Tests for Business-Linked Authorization).

测试场景：
1. 部门负责人角色推断
2. 产品负责人角色推断
3. 项目负责人角色推断
4. 虚拟团队负责人角色推断
5. 动态权限标识聚合
"""

import uuid

from devops_collector.core.business_auth import get_business_linked_roles, get_dynamic_permissions
from devops_collector.models.base_models import (
    Organization,
    Product,
    ProjectMaster,
    SysMenu,
    SysRole,
    SysRoleMenu,
    Team,
    User,
)
from devops_collector.plugins.gitlab.models import (
    GitLabGroup,
    GitLabGroupMember,
    GitLabProject,
    GitLabProjectMember,
)


def test_get_business_linked_roles_should_return_dept_manager_when_user_is_org_manager(db_session):
    user_id = uuid.uuid4()
    user = User(global_user_id=user_id, username="manager", full_name="Manager")
    db_session.add(user)
    db_session.flush()  # Ensure user exists before being referenced as manager

    org = Organization(org_code="ORG_DEPT_1", org_name="Test Org", manager_user_id=user_id, is_current=True, sync_version=1)
    db_session.add(org)
    db_session.flush()

    # execution
    roles = get_business_linked_roles(db_session, user_id)

    # validation
    assert "DEPT_MANAGER" in roles


def test_get_business_linked_roles_should_return_product_manager_when_user_is_pm(db_session):
    # Setup
    user_id = uuid.uuid4()
    user = User(global_user_id=user_id, username="pm", full_name="PM")
    db_session.add(user)
    db_session.flush()

    product = Product(
        product_code="PROD_CODE_1",
        product_name="Test Product",
        product_description="Test",
        version_schema="SemVer",
        product_manager_id=user_id,
        is_current=True,
        sync_version=1,
    )
    db_session.add(product)
    db_session.flush()

    # execution
    roles = get_business_linked_roles(db_session, user_id)

    # validation
    assert "PRODUCT_MANAGER" in roles


def test_get_business_linked_roles_should_return_project_manager_when_user_is_project_lead(db_session):
    # Setup
    user_id = uuid.uuid4()
    user = User(global_user_id=user_id, username="pl", full_name="PL")
    db_session.add(user)
    db_session.flush()

    project = ProjectMaster(project_code="PROJ_001", project_name="Test Project", pm_user_id=user_id, is_current=True, sync_version=1)
    db_session.add(project)
    db_session.flush()

    # execution
    roles = get_business_linked_roles(db_session, user_id)

    # validation
    assert "PROJECT_MANAGER" in roles


def test_get_business_linked_roles_should_return_dept_manager_when_user_is_team_leader(db_session):
    # Setup
    user_id = uuid.uuid4()
    user = User(global_user_id=user_id, username="tl", full_name="TL")
    db_session.add(user)
    db_session.flush()

    team = Team(name="Test Team", team_code="TEAM_001", leader_id=user_id, is_current=True, sync_version=1)
    db_session.add(team)
    db_session.flush()

    # execution
    roles = get_business_linked_roles(db_session, user_id)

    # validation
    assert "DEPT_MANAGER" in roles


def test_get_dynamic_permissions_should_aggregate_all_perms_from_business_roles(db_session):
    # Setup roles and menus
    # 1. Roles
    dept_role = SysRole(role_name="Dept Manager", role_key="DEPT_MANAGER")
    pm_role = SysRole(role_name="Product Manager", role_key="PRODUCT_MANAGER")
    db_session.add_all([dept_role, pm_role])

    # 2. Menus
    menu1 = SysMenu(menu_name="Org View", perms="org:view", status=True)
    menu2 = SysMenu(menu_name="Prod Manage", perms="prod:manage", status=True)
    db_session.add_all([menu1, menu2])
    db_session.flush()

    # 3. Role-Menu Matrix
    db_session.add(SysRoleMenu(role_id=dept_role.id, menu_id=menu1.id))
    db_session.add(SysRoleMenu(role_id=pm_role.id, menu_id=menu2.id))

    # 4. User acting as both Org Manager and Product Manager
    user_id = uuid.uuid4()
    user = User(global_user_id=user_id, username="boss", full_name="Boss")
    db_session.add(user)
    db_session.flush()

    org = Organization(org_code="O1", org_name="O1", manager_user_id=user_id, is_current=True, sync_version=1)
    prod = Product(
        product_code="P1",
        product_name="P1",
        product_description="P1",
        version_schema="S",
        product_manager_id=user_id,
        is_current=True,
        sync_version=1,
    )
    db_session.add_all([org, prod])
    db_session.flush()

    # execution
    perms = get_dynamic_permissions(db_session, user_id)

    # validation
    assert "org:view" in perms
    assert "prod:manage" in perms
    assert len(perms) == 2


def test_get_business_linked_roles_should_return_empty_for_normal_user(db_session):
    user_id = uuid.uuid4()
    roles = get_business_linked_roles(db_session, user_id)
    assert len(roles) == 0


def test_get_business_linked_roles_should_return_dept_manager_when_user_is_gitlab_group_maintainer(db_session):
    # Setup
    user_id = uuid.uuid4()
    user = User(global_user_id=user_id, username="gitlab_boss", full_name="GitLab Boss")
    db_session.add(user)

    # Create GitLab Group and Membership
    # Note: access_level = 40 (Maintainer)
    group = GitLabGroup(id=101, name="Core Group", full_path="core")
    db_session.add(group)
    db_session.flush()

    membership = GitLabGroupMember(group_id=101, user_id=user_id, access_level=40)
    db_session.add(membership)
    db_session.flush()

    # execution
    roles = get_business_linked_roles(db_session, user_id)

    # validation
    assert "DEPT_MANAGER" in roles


def test_get_business_linked_roles_should_return_project_manager_when_user_is_gitlab_project_maintainer(db_session):
    # Setup
    user_id = uuid.uuid4()
    user = User(global_user_id=user_id, username="gitlab_pm", full_name="GitLab PM")
    db_session.add(user)

    # Create GitLab Project and Membership
    # Note: access_level = 50 (Owner)
    project = GitLabProject(id=201, name="Web App", path_with_namespace="core/webapp")
    db_session.add(project)
    db_session.flush()

    membership = GitLabProjectMember(project_id=201, user_id=user_id, access_level=50)
    db_session.add(membership)
    db_session.flush()

    # execution
    roles = get_business_linked_roles(db_session, user_id)

    # validation
    assert "PROJECT_MANAGER" in roles

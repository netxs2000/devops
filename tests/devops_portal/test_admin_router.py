import pytest
from devops_collector.models.base_models import IdentityMapping, Team, Organization, ProjectMaster
from devops_collector.plugins.gitlab.models import GitLabProject

def test_list_users(authenticated_client, db_session, mock_user):
    # mock_user is already created but not added to session in the fixture? 
    # Wait, the mock_user fixture just returns an object, devops_portal.dependencies.get_current_user returns it.
    # But for list_users to return it, it must be in the DB.
    # The fixture mock_user has id=1.
    
    # Let's add the user to DB
    db_session.add(mock_user)
    db_session.commit()

    response = authenticated_client.get("/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["email"] == "test@example.com"

def test_list_identity_mappings(authenticated_client, db_session, mock_user):
    db_session.add(mock_user)
    mapping = IdentityMapping(
        global_user_id=mock_user.global_user_id,
        source_system="gitlab",
        external_user_id="100",
        external_username="testuser_ext"
    )
    db_session.add(mapping)
    db_session.commit()

    response = authenticated_client.get("/admin/identity-mappings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["external_username"] == "testuser_ext"

def test_create_identity_mapping(authenticated_client, db_session, mock_user):
    # Mock user must have SYSTEM_ADMIN role
    # The default mock_user in conftest has 'role="admin"', but code checks 'SYSTEM_ADMIN' in user.roles list?
    # devops_portal/dependencies.py: user_role_codes = [r.code for r in current_user.roles]
    # So I need to add a Role object to the user.
    from devops_collector.models.base_models import Role, UserRole
    
    db_session.add(mock_user)
    role = Role(code="SYSTEM_ADMIN", name="System Admin")
    db_session.add(role)
    db_session.commit()
    
    user_role = UserRole(user_id=mock_user.global_user_id, role_id=role.id)
    db_session.add(user_role)
    db_session.commit()
    
    # Reload mock_user to get relationships because the fixture is just an object.
    # Actually authenticated_client uses the mock_user object from fixture.
    # The fixture object doesn't have the relationship loaded from DB unless I refresh it.
    # But dependencies.get_current_user returns the mock_object directly lambda: mock_user.
    # So I should update the mock_user object manually or change get_current_user to fetch from DB.
    # modifying the object locally:
    mock_user.roles = [role]

    payload = {
        "global_user_id": str(mock_user.global_user_id),
        "source_system": "jira",
        "external_user_id": "J123",
        "external_username": "jira_user",
        "external_email": "jira@example.com"
    }

    response = authenticated_client.post("/admin/identity-mappings", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    mapping = db_session.query(IdentityMapping).filter_by(source_system="jira").first()
    assert mapping is not None

def test_list_teams(authenticated_client, db_session):
    team = Team(name="Team A", team_code="TEAM-A")
    db_session.add(team)
    db_session.commit()

    response = authenticated_client.get("/admin/teams")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Team A"

def test_list_mdm_projects(authenticated_client, db_session):
    org = Organization(org_id="ORG1", org_name="Org 1")
    db_session.add(org)
    project = ProjectMaster(
        project_id="PROJ1", project_name="Project 1", 
        org_id="ORG1", status="PLAN"
    )
    db_session.add(project)
    db_session.commit()

    response = authenticated_client.get("/admin/mdm-projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["project_name"] == "Project 1"


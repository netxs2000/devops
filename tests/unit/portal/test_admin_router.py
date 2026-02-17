import pytest
from devops_collector.models.base_models import IdentityMapping, Team, Organization, ProjectMaster
from devops_collector.plugins.gitlab.models import GitLabProject

def test_list_users(authenticated_client, db_session):
    response = authenticated_client.get("/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(u["email"] == "test@example.com" for u in data)

def test_list_identity_mappings(authenticated_client, db_session):
    # User is already in DB from fixture
    from devops_collector.models.base_models import User
    user = db_session.query(User).filter_by(primary_email="test@example.com").first()
    
    mapping = IdentityMapping(
        global_user_id=user.global_user_id,
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

def test_create_identity_mapping(authenticated_client, db_session):
    from devops_collector.models.base_models import User
    user = db_session.query(User).filter_by(primary_email="test@example.com").first()

    payload = {
        "global_user_id": str(user.global_user_id),
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



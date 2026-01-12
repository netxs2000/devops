import pytest
from devops_collector.plugins.jenkins.models import JenkinsJob, JenkinsBuild
from devops_collector.plugins.jfrog.models import JFrogArtifact
from devops_collector.plugins.nexus.models import NexusComponent
from devops_collector.models.dependency import DependencyScan
from devops_collector.plugins.gitlab.models import GitLabProject

def test_api_root(client):
    """Test the static file mount (root)."""
    # Just check if it returns 200 or 404 depending on if index.html exists
    # If not existing, it returns 404, if exists 200.
    # We are mocking the filesystem so it might be tricky.
    response = client.get("/")
    # Check if we get 200 or 404, just ensure no 500
    assert response.status_code in [200, 404]

def test_list_jenkins_jobs(authenticated_client, db_session):
    # Setup data
    job = JenkinsJob(
        name="test-job",
        full_name="test-job",
        url="http://jenkins/job/test-job"
    )
    db_session.add(job)
    db_session.commit()

    response = authenticated_client.get("/jenkins/jobs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test-job"

def test_list_jenkins_builds(authenticated_client, db_session):
    job = JenkinsJob(
        name="test-job",
        full_name="test-job",
        url="http://jenkins/job/test-job"
    )
    db_session.add(job)
    db_session.commit()
    
    build = JenkinsBuild(
        job_id=job.id,  
        number=1,
        result="SUCCESS",
        url="http://jenkins/job/test-job/1"
    )
    db_session.add(build)
    db_session.commit()

    response = authenticated_client.get(f"/jenkins/jobs/{job.id}/builds")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["number"] == 1

def test_gitlab_webhook(client):
    payload = {
        "object_kind": "issue", 
        "object_attributes": {
            "id": 123, 
            "iid": 1, 
            "action": "update",
            "state": "opened"
        },
        "project": {"id": 1, "name": "test-project"},
        "labels": [{"title": "type::test"}]
    }
    headers = {"X-Gitlab-Event": "Issue Hook"}
    response = client.post("/webhook", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}

def test_list_jfrog_artifacts(authenticated_client, db_session):
    artifact = JFrogArtifact(
        repo="libs-release-local",
        path="com/example/test",
        name="test-artifact",
        version="1.0.0",
        package_type="maven"
    )
    db_session.add(artifact)
    db_session.commit()

    response = authenticated_client.get("/artifacts/jfrog")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test-artifact"

def test_list_nexus_components(authenticated_client, db_session):
    comp = NexusComponent(
        name="test-comp",
        repository="maven-releases",
        group="com.example",
        version="1.0.0"
    )
    db_session.add(comp)
    db_session.commit()

    response = authenticated_client.get("/artifacts/nexus")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test-comp"

def test_list_dependency_scans(authenticated_client, db_session):
    project = GitLabProject(
        name="test-project",
        # path is likely 'path_with_namespace' in GitLabProject model
        path_with_namespace="test/project"
    )
    db_session.add(project)
    db_session.commit()
    
    scan = DependencyScan(
        project_id=project.id,
        commit_sha="abc1234",
        status="success"
    )
    db_session.add(scan)
    db_session.commit()

    response = authenticated_client.get("/security/dependency-scans")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "success"

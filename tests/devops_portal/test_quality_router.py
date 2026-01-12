import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from devops_collector.config import Config
from devops_portal.routers.quality_router import get_test_management_service

def test_province_quality(authenticated_client, mock_user):
    # Mock httpx response in Config.http_client
    # Config.http_client is an AsyncClient instance initiated in lifespan
    # But in tests we don't run lifespan.
    # However the code uses Config.http_client directly.
    # In conftest we haven't mocked Config.http_client.
    
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value=[
        {"labels": ["province::Liaoning", "type::bug"]},
        {"labels": ["province::Beijing", "type::bug"]},
        {"labels": ["province::Liaoning"]}
    ])
    
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    
    Config.http_client = mock_client
    
    # Mock user location
    from devops_collector.models.base_models import Location
    mock_user.location = Location(short_name="Liaoning")
    
    response = authenticated_client.get("/quality/projects/1/province-quality")
    assert response.status_code == 200
    data = response.json()
    # Should only return Liaoning data because of user location filter
    assert len(data) == 1
    assert data[0]["province"] == "Liaoning"
    assert data[0]["bug_count"] == 1

@pytest.mark.asyncio
async def test_quality_gate(authenticated_client):
    mock_service = AsyncMock()
    
    # Mock requirements
    req1 = MagicMock(iid=1, review_state='approved')
    mock_service.list_requirements.return_value = [req1]
    
    # Mock requirement details (test cases)
    detail1 = MagicMock(test_cases=[1])
    mock_service.get_requirement_detail.return_value = detail1
    
    # Mock issues (P0 bugs)
    mock_client = MagicMock()
    mock_client.get_project_issues.return_value = [
        {"labels": ["type::bug", "severity::S0", "state:opened"]}
    ] # Has P0 bug
    
    # Mock pipelines
    mock_client.get_project_pipelines.return_value = [{"status": "success"}]
    
    mock_service.client = mock_client
    
    from devops_portal.main import app
    app.dependency_overrides[get_test_management_service] = lambda: mock_service
    
    try:
        response = authenticated_client.get("/quality/projects/1/quality-gate")
        assert response.status_code == 200
        data = response.json()
        assert data["p0_bugs_cleared"] == False # We simulated one P0 bug
        assert data["is_passed"] == False
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_mr_summary(authenticated_client):
    mock_service = AsyncMock()
    mock_service.get_mr_summary_stats.return_value = {
        "open_mrs": 5, "merged_mrs": 10, "avg_review_time": 2.5
    }
    
    from devops_portal.main import app
    app.dependency_overrides[get_test_management_service] = lambda: mock_service
    
    try:
        response = authenticated_client.get("/quality/projects/1/mr-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["open_mrs"] == 5
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_quality_report(authenticated_client):
    mock_service = AsyncMock()
    mock_service.generate_quality_report.return_value = "## Report"
    
    from devops_portal.main import app
    app.dependency_overrides[get_test_management_service] = lambda: mock_service
    
    try:
        response = authenticated_client.get("/quality/projects/1/quality-report")
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "## Report"
    finally:
        app.dependency_overrides = {}

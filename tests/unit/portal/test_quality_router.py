import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from devops_collector.config import Config
from devops_portal.routers.quality_router import get_quality_service

def test_province_quality(authenticated_client, mock_user, monkeypatch):
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

    # Use monkeypatch to temporarily replace Config.http_client
    monkeypatch.setattr(Config, 'http_client', mock_client)

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

    # Mock the quality gate status method directly
    mock_service.get_quality_gate_status.return_value = {
        "is_passed": False,
        "requirements_covered": True,
        "p0_bugs_cleared": False,
        "pipeline_stable": True,
        "regional_risk_free": True,
        "summary": "Quality gate failed due to P0 bugs"
    }

    from devops_portal.main import app
    app.dependency_overrides[get_quality_service] = lambda: mock_service

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
    mock_service.get_mr_analytics.return_value = {
        "total": 15,
        "merged": 10,
        "opened": 5,
        "closed": 0,
        "approved": 8,
        "rework_needed": 2,
        "rejected": 1,
        "avg_discussions": 3.2,
        "avg_merge_time_hours": 2.5
    }

    from devops_portal.main import app
    app.dependency_overrides[get_quality_service] = lambda: mock_service

    try:
        response = authenticated_client.get("/quality/projects/1/mr-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["opened"] == 5
        assert data["merged"] == 10
    finally:
        app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_get_quality_report(authenticated_client):
    mock_service = AsyncMock()
    mock_service.generate_report.return_value = "## Report"
    
    from devops_portal.main import app
    app.dependency_overrides[get_quality_service] = lambda: mock_service
    
    try:
        response = authenticated_client.get("/quality/projects/1/quality-report")
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "## Report"
    finally:
        app.dependency_overrides = {}

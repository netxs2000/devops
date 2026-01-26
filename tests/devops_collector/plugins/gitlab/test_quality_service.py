"""Unit tests for GitLab Quality Service."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from devops_collector.plugins.gitlab.quality_service import QualityService
from devops_portal import schemas

@pytest.fixture
def mock_client():
    """Mock GitLabClient."""
    return MagicMock()

@pytest.fixture
def quality_service(db_session, mock_client):
    """Initialize QualityService with mocks."""
    return QualityService(db_session, mock_client)

@pytest.fixture
def anyio_backend():
    return 'asyncio'

class TestQualityService:
    """Tests for QualityService."""

    @pytest.mark.anyio
    async def test_get_quality_gate_status_should_pass_when_all_criteria_met(self, quality_service, mock_client):
        """Test quality gate status when all health criteria are satisfied."""
        # 1. Mock requirements and coverage
        mock_req = schemas.RequirementSummary(iid=1, title="R1", state="opened", review_state="approved")
        
        # We need to mock the internal test_service calls
        # Since QualityService creates instance of TestManagementService in __init__, 
        # we might need to mock TestManagementService class or its methods on the instance.
        with patch.object(quality_service.test_service, 'list_requirements', new_callable=AsyncMock) as mock_list, \
             patch.object(quality_service.test_service, 'get_requirement_detail', new_callable=AsyncMock) as mock_detail:
            
            mock_list.return_value = [mock_req]
            mock_detail.return_value = schemas.RequirementDetail(
                id=1, iid=1, title="R1", state="opened", review_state="approved",
                test_cases=[MagicMock()] # Has 1 test case -> 100% coverage
            )
            
            # 2. Mock client issues (for Bug check)
            mock_client.get_project_issues.return_value = [
                {'labels': ['type::bug', 'severity::S1'], 'state': 'opened'} # S1 is not S0
            ]
            
            # 3. Mock pipelines
            mock_client.get_project_pipelines.return_value = [{'status': 'success'}]
            
            status = await quality_service.get_quality_gate_status(1, None)
            
            assert status.is_passed is True
            assert status.requirements_covered is True
            assert status.p0_bugs_cleared is True
            assert status.pipeline_stable is True

    @pytest.mark.anyio
    async def test_get_quality_gate_status_should_fail_when_p0_bug_exists(self, quality_service, mock_client):
        """Test quality gate failure when a critical P0 bug is present."""
        with patch.object(quality_service.test_service, 'list_requirements', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [] # No requirements -> coverage check trivial or false?
            # In code: if approved_reqs: ... else req_covered = False (default)
            # Actually if no reqs, it will be False.
            
            mock_client.get_project_issues.return_value = [
                {'labels': ['type::bug', 'severity::S0'], 'state': 'opened'} # P0 Bug
            ]
            mock_client.get_project_pipelines.return_value = [{'status': 'success'}]
            
            status = await quality_service.get_quality_gate_status(1, None)
            
            assert status.is_passed is False
            assert status.p0_bugs_cleared is False

    @pytest.mark.anyio
    async def test_get_mr_analytics_should_delegate_to_test_service(self, quality_service):
        """Test MR analytics delegation."""
        with patch.object(quality_service.test_service, 'get_mr_summary_stats', new_callable=AsyncMock) as mock_stats:
            mock_stats.return_value = {'total': 5}
            res = await quality_service.get_mr_analytics(1)
            assert res['total'] == 5
            mock_stats.assert_called_once_with(1)

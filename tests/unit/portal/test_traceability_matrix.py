
import pytest
from unittest.mock import MagicMock, AsyncMock
from devops_collector.plugins.gitlab.test_management_service import TestManagementService
from devops_collector.plugins.zentao.models import ZenTaoProduct, ZenTaoIssue
from devops_collector.models.base_models import TraceabilityLink
from devops_collector.models.test_management import GTMTestCase

@pytest.mark.asyncio
async def test_get_aggregated_requirements_service_logic():
    # Mock DB Session
    mock_db = MagicMock()
    mock_client = MagicMock()
    
    service = TestManagementService(mock_db, mock_client)
    
    # --- Mock Data Setup ---
    product_id = "PRD-TEST"
    
    # 1. Mock finding ProjectProductRelation
    mock_relation = MagicMock()
    mock_relation.project_id = "MDM-PROJ-1"
    
    # 2. Mock finding GitLabProject
    mock_gp = MagicMock()
    mock_gp.id = 101
    
    # 3. Mock finding ZenTaoProduct via GitLab ID
    mock_zp_git = MagicMock()
    mock_zp_git.id = 1001
    
    # 4. Mock finding ZenTaoProduct via Code
    mock_zp_code = MagicMock()
    mock_zp_code.id = 1002

    # 5. Mock finding ZenTaoIssue
    mock_issue = MagicMock()
    mock_issue.id = 5001
    mock_issue.title = "User Login"
    mock_issue.status = "active"
    mock_issue.type = "story"

    # 6. Mock Traceability Links
    link_mr = MagicMock()
    link_mr.target_type = 'merge_request'
    link_mr.target_id = '123'
    
    # 7. Mock GTMTestCase (New)
    mock_case = MagicMock()
    mock_case.id = 701
    mock_case.iid = 1
    mock_case.project_id = 101
    mock_case.title = "Verify User Login #5001" # Contains Req ID
    mock_case.description = "Test steps"
    mock_case.execution_count = 1
    mock_case.project.name = "GitLab Proj A"

    # --- Configuring the Query Chain ---
    query_mock = mock_db.query.return_value
    filter_mock = query_mock.filter.return_value
    
    # Side effects for .all() calls in sequence:
    # 1. ProjectProductRelation (filter by product_id)
    # 2. GitLabProject (filter by mdm_project_id)
    # 3. ZenTaoProduct (filter by gitlab_project_id)
    # 4. ZenTaoProduct (filter by code)
    # 5. ZenTaoIssue (filter by product_id list)
    # 6. GTMTestCase (filter by project_id list) -> New call added
    # 7. TraceabilityLink (filter by source_id)
    
    filter_mock.all.side_effect = [
        [mock_relation],       # 1
        [mock_gp],             # 2
        [mock_zp_git],             # 3
        [mock_zp_code],        # 4
        [mock_issue],          # 5
        [mock_case],           # 6 (Found Test Cases)
        [link_mr]              # 7 (Links for Issue 5001)
    ]

    # --- Execute ---
    results = await service.get_aggregated_requirements(mock_db, MagicMock(), product_id=product_id)
    
    # --- Assertions ---
    assert len(results) == 1
    item = results[0]
    
    # Check Traceability logic
    # Test Case should be linked because title contains "#5001"
    assert len(item.test_cases) == 1
    assert item.test_cases[0].title == "Verify User Login #5001"
    
    assert len(item.merge_requests) == 1
    assert item.merge_requests[0]['iid'] == '123'

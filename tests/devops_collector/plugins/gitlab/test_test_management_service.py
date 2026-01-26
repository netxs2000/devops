"""Unit tests for GitLab Test Management Service and Parser."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from devops_collector.plugins.gitlab.test_management_service import TestManagementService
from devops_collector.plugins.gitlab.parser import GitLabTestParser
from devops_collector.plugins.gitlab.models import GitLabProject
from devops_collector.models.base_models import ProjectProductRelation
from devops_portal import schemas

@pytest.fixture
def mock_client():
    """Mock GitLabClient for testing."""
    client = MagicMock()
    return client

@pytest.fixture
def service(db_session, mock_client):
    """Initialize TestManagementService with mocked dependencies."""
    return TestManagementService(db_session, mock_client)

@pytest.fixture
def anyio_backend():
    return 'asyncio'

class TestGitLabTestParser:
    """Tests for GitLabTestParser."""

    def test_parse_description_should_return_structured_data(self):
        """Test parsing a valid GitLab issue description into structured test case data."""
        description = """## 📝 测试用例详情
- **用例优先级**: [P1]
- **测试类型**: [性能测试]
- **关联需求**: # 100

## 🛠️ 前置条件
- [ ] 已准备好测试环境
- [ ] 测试数据已导入
---

## 🚀 执行步骤
1. **操作描述**: 运行压测脚本
   **反馈**: 系统响应正常
2. **操作描述**: 停止压测
   **反馈**: 资源稳步下降
"""
        result = GitLabTestParser.parse_description(description)
        assert result['priority'] == 'P1'
        assert result['test_type'] == '性能测试'
        assert "已准备好测试环境" in result['pre_conditions']
        assert len(result['test_steps']) == 2
        assert result['test_steps'][0]['action'] == "运行压测脚本"
        assert result['test_steps'][0]['expected'] == "系统响应正常"

    def test_parse_description_should_handle_empty_description(self):
        """Test parsing an empty or None description."""
        result = GitLabTestParser.parse_description("")
        assert result['priority'] == 'P2'
        assert result['test_type'] == '功能测试'
        assert result['test_steps'] == []

    def test_extract_requirement_id_should_work(self):
        """Test extracting requirement ID from description."""
        description = "关联需求]: # 123"
        assert GitLabTestParser.extract_requirement_id(description) == 123
        assert GitLabTestParser.extract_requirement_id("No id here") is None

class TestTestManagementService:
    """Tests for TestManagementService."""

    @pytest.mark.anyio
    async def test_get_test_cases_should_return_parsed_cases(self, service, mock_client, db_session):
        """Test fetching and parsing test cases from a project."""
        # Setup DB
        project = GitLabProject(id=1, name="Test Project")
        db_session.add(project)
        db_session.commit()
        
        # Setup Mock Client
        mock_client.get_project_issues.return_value = [
            {
                'id': 101, 'iid': 1, 'title': 'Test Case 1', 
                'labels': ['type::test', 'status::passed'],
                'description': '## 📝 测试用例详情\n- **用例优先级**: [P1]\n- **测试类型**: [Functional]\n',
                'web_url': 'http://gitlab/1'
            }
        ]
        
        cases = await service.get_test_cases(db_session, 1, None)
        assert len(cases) == 1
        assert cases[0].title == "Test Case 1"
        assert cases[0].priority == "P1"
        assert cases[0].result == "passed"

    @pytest.mark.anyio
    async def test_create_test_case_should_call_client(self, service, mock_client):
        """Test creating a new test case in GitLab."""
        mock_client.create_issue.return_value = {'iid': 55}
        
        steps = [{"action": "Click Button", "expected": "Success"}]
        await service.create_test_case(
            project_id=1, title="New TC", priority="P2", test_type="UI",
            pre_conditions=["Init state"], steps=steps
        )
        
        mock_client.create_issue.assert_called_once()
        args, kwargs = mock_client.create_issue.call_args
        assert args[0] == 1 # project_id
        payload = args[1]
        assert "New TC" == payload['title']
        assert "type::test" in payload['labels']
        assert "## 🛠️ 前置条件" in payload['description']
        assert "Click Button" in payload['description']

    @pytest.mark.anyio
    async def test_execute_test_case_should_update_gitlab(self, service, mock_client):
        """Test executing a test case and recording the result in GitLab."""
        mock_client.get_project_issue.return_value = {'labels': ['type::test', 'status::pending']}
        
        success = await service.execute_test_case(1, 10, "passed", "Tester Alpha")
        
        assert success is True
        mock_client.update_issue.assert_called_once()
        mock_client.add_issue_note.assert_called_once()
        
        # Verify labels updated
        update_args = mock_client.update_issue.call_args[0]
        # In service.py: self.client.update_issue(project_id, issue_iid, {'labels': ','.join(new_labels)})
        assert "status::passed" in update_args[2]['labels']
        assert "status::pending" not in update_args[2]['labels']

    @pytest.mark.anyio
    async def test_get_aggregated_test_cases_should_work(self, service, mock_client, db_session):
        """Test aggregating test cases across multiple projects based on product association."""
        # Setup DB data
        p1 = GitLabProject(id=1, name="P1", mdm_project_id=1001)
        rel = ProjectProductRelation(product_id="PROD1", project_id=1001, org_id="ORG1")
        db_session.add_all([p1, rel])
        db_session.commit()
        
        # Mock client for get_test_cases (called internally)
        mock_client.get_project_issues.return_value = []
        
        cases = await service.get_aggregated_test_cases(db_session, None, product_id="PROD1")
        assert isinstance(cases, list)
        mock_client.get_project_issues.assert_called_with(1)

    @pytest.mark.anyio
    async def test_get_requirement_detail_should_return_linked_cases(self, service, mock_client):
        """Test fetching requirement details with its linked test cases."""
        # Mock requirement issue
        mock_client.get_project_issue.return_value = {
            'id': 200, 'iid': 2, 'title': 'Req 1', 'state': 'opened',
            'labels': ['type::requirement', 'review-state::approved'],
            'description': 'Acceptance Criteria'
        }
        
        # Mock multiple issues in project, one linked to this requirement
        mock_client.get_project_issues.return_value = [
            {
                'id': 101, 'iid': 1, 'title': 'Linked Test', 
                'labels': ['type::test'],
                'description': '关联需求]: # 2\n## 📝 测试用例详情\n- **用例优先级**: [P1]\n- **测试类型**: [UI]',
                'web_url': 'http://gitlab/1'
            },
            {
                'id': 102, 'iid': 3, 'title': 'Unlinked Test', 
                'labels': ['type::test'],
                'description': 'Other desc',
                'web_url': 'http://gitlab/3'
            }
        ]
        
        detail = await service.get_requirement_detail(1, 2)
        assert detail is not None
        assert detail.iid == 2
        assert len(detail.test_cases) == 1
        assert detail.test_cases[0].title == "Linked Test"

    @pytest.mark.anyio
    async def test_batch_import_test_cases_should_work(self, service, mock_client):
        """Test batch importing multiple test cases."""
        mock_client.create_issue.side_effect = [{'iid': 10}, {'iid': 11}]
        
        items = [
            {'title': 'T1', 'priority': 'P1', 'test_type': 'A', 'pre_conditions': [], 'steps': []},
            {'title': 'T2', 'priority': 'P2', 'test_type': 'B', 'pre_conditions': [], 'steps': []}
        ]
        
        result = await service.batch_import_test_cases(1, items)
        assert result['imported_count'] == 2
        assert 10 in result['iids']
        assert 11 in result['iids']

    @pytest.mark.anyio
    async def test_get_mr_summary_stats_should_calculate_correctly(self, service, mock_client):
        """Test calculating MR summary statistics."""
        mock_client.get_project_merge_requests.return_value = [
            {'state': 'merged', 'created_at': '2023-01-01T10:00:00Z', 'merged_at': '2023-01-01T12:00:00Z'},
            {'state': 'opened'},
            {'state': 'closed'}
        ]
        
        stats = await service.get_mr_summary_stats(1)
        assert stats['total_count'] == 3
        assert stats['merged_count'] == 1
        assert stats['avg_merge_time'] == 2.0 # 2 hours

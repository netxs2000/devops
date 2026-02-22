"""测试用例解析与服务逻辑单元测试。

验证 GitLabTestParser 和 TestManagementService 的核心解析与业务逻辑。
"""
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.plugins.gitlab.parser import GitLabTestParser
from devops_collector.plugins.gitlab.test_management_service import TestManagementService


# --- GitLabTestParser 单元测试 ---

def test_parser_should_extract_priority_and_type():
    description = """
[用例优先级]: [P0]
[测试类型]: [Security]
## 🛠️ 前置条件
- [ ] User is logged in
---
## 🚀 执行步骤
1. **操作描述**: Click delete
   **反馈**: Success
"""
    result = GitLabTestParser.parse_description(description)
    assert result['priority'] == 'P0'
    assert result['test_type'] == 'Security'
    assert "User is logged in" in result['pre_conditions']
    assert len(result['test_steps']) == 1
    assert result['test_steps'][0]['action'] == "Click delete"

def test_parser_should_extract_requirement_id():
    description = "关联需求]: # 1234"
    iid = GitLabTestParser.extract_requirement_id(description)
    assert iid == 1234

def test_parser_should_handle_empty_description():
    result = GitLabTestParser.parse_description("")
    assert result['priority'] == 'P2'
    assert result['test_steps'] == []

@pytest.fixture
def anyio_backend():
    return 'asyncio'

# --- TestManagementService 单元测试 ---

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_client():
    return MagicMock(spec=GitLabClient)

@pytest.fixture
def service(mock_db, mock_client):
    return TestManagementService(mock_db, mock_client)

@pytest.mark.anyio
async def test_get_test_cases_should_parse_gitlab_issues(service, mock_client, mock_db):
    # Mock GitLab API 返回的数据
    mock_issues = [
        {
            'id': 1,
            'iid': 101,
            'title': 'Test Login',
            'labels': ['type::test', 'status::passed'],
            'description': '[用例优先级]: [P1]\n[测试类型]: [Functional]',
            'web_url': 'http://gitlab/issue/101'
        },
        {
            'id': 2,
            'iid': 102,
            'title': 'Non-test issue',
            'labels': ['type::bug'],
            'description': '',
            'web_url': ''
        }
    ]
    mock_client.get_project_issues.return_value = mock_issues
    mock_db.query().filter().first.return_value = None # No project info found in DB

    cases = await service.get_test_cases(mock_db, 1, MagicMock())

    assert len(cases) == 1
    assert cases[0].iid == 101
    assert cases[0].result == 'passed'
    assert cases[0].priority == 'P1'

@pytest.mark.anyio
async def test_execute_test_case_should_update_labels_and_add_note(service, mock_client):
    project_id = 1
    issue_iid = 101
    mock_client.get_project_issue.return_value = {'labels': ['type::test', 'status::pending']}

    success = await service.execute_test_case(project_id, issue_iid, 'passed', 'Tester Zhang')

    assert success is True
    # 验证是否调用了更新接口，且移除了之前的 status 标签
    mock_client.update_issue.assert_called_once()
    args, kwargs = mock_client.update_issue.call_args
    # update_issue(project_id, issue_iid, data) -> data is args[2]
    update_data = args[2] if len(args) > 2 else kwargs.get('data', {})
    assert 'status::passed' in update_data['labels']
    assert 'status::pending' not in update_data['labels']

    # 验证是否添加了记录
    mock_client.add_issue_note.assert_called_once()
    note_args = mock_client.add_issue_note.call_args[0]
    assert 'Tester Zhang' in note_args[2]

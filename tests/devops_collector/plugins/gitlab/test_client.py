
import unittest
from unittest.mock import MagicMock, patch, Mock
import requests
from devops_collector.plugins.gitlab.client import GitLabClient

class TestGitLabClient(unittest.TestCase):
    def setUp(self):
        self.url = "https://gitlab.example.com"
        self.token = "my-token"
        self.client = GitLabClient(self.url, self.token)
        # Mock the requests.get used in BaseClient._get, but actually we should mock _get directly
        # since we want to test GitLabClient logic, not BaseClient logic which should be tested separately.
        # However, calling _get calls super()._get, so we can mock requests.get or mock _get.
        # It is easier to mock _get on the client instance if we want to isolate GitLabClient logic.
        self.client._get = MagicMock()

    def test_init(self):
        self.assertEqual(self.client.base_url, "https://gitlab.example.com/api/v4")
        self.assertEqual(self.client.headers, {'PRIVATE-TOKEN': 'my-token'})

    def test_test_connection_success(self):
        self.client._get.return_value.ok = True
        self.assertTrue(self.client.test_connection())
        self.client._get.assert_called_with("version")

    def test_test_connection_failure(self):
        self.client._get.side_effect = Exception("Connection error")
        self.assertFalse(self.client.test_connection())

    def test_get_project(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "Test Project"}
        self.client._get.return_value = mock_response

        project = self.client.get_project(1)
        self.assertEqual(project['name'], "Test Project")
        self.client._get.assert_called_with("projects/1", params={'statistics': True})

    def test_get_group(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "name": "Test Group"}
        self.client._get.return_value = mock_response

        group = self.client.get_group("mybuffer")
        self.assertEqual(group['name'], "Test Group")
        self.client._get.assert_called_with("groups/mybuffer")

    def test_get_project_commits_generator(self):
        # Mock pagination
        # Page 1 returns 2 items, Page 2 returns 1 item, Page 3 returns empty (stop)
        
        # Setup _get to return different values based on call args
        def side_effect(endpoint, params=None):
            if endpoint != "projects/1/repository/commits":
                return MagicMock()
            
            page = params.get('page')
            mock_resp = MagicMock()
            if page == 1:
                mock_resp.json.return_value = [{"id": "c1"}, {"id": "c2"}]
            elif page == 2:
                mock_resp.json.return_value = [{"id": "c3"}]
            else:
                mock_resp.json.return_value = []
            return mock_resp

        self.client._get.side_effect = side_effect

        commits = list(self.client.get_project_commits(1, per_page=2))
        self.assertEqual(len(commits), 3)
        self.assertEqual(commits[0]['id'], "c1")
        self.assertEqual(commits[2]['id'], "c3")
        
        # Verify calls
        # Expected calls: page 1, page 2, page 3
        self.assertEqual(self.client._get.call_count, 3)

    def test_get_project_issues_with_since(self):
        def side_effect(endpoint, params=None):
            mock_resp = MagicMock()
            if params.get('page') == 1:
                mock_resp.json.return_value = [{"id": 1}]
            else:
                mock_resp.json.return_value = []
            return mock_resp
            
        self.client._get.side_effect = side_effect
        
        issues = list(self.client.get_project_issues(1, since="2023-01-01T00:00:00Z"))
        self.assertEqual(len(issues), 1)
        
        # Verify call args include updated_after
        calls = self.client._get.call_args_list
        self.assertTrue('updated_after' in calls[0][1]['params'])
        self.assertEqual(calls[0][1]['params']['updated_after'], "2023-01-01T00:00:00Z")

    def test_get_commit_diff(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"diff": "..."}]
        self.client._get.return_value = mock_resp
        
        diffs = self.client.get_commit_diff(1, "sha1")
        self.assertEqual(len(diffs), 1)
        self.client._get.assert_called_with("projects/1/repository/commits/sha1/diff")

    def test_get_project_merge_requests(self):
        self.client._get.return_value.json.return_value = [{"id": 1}]
        result = list(self.client.get_project_merge_requests(1))
        self.assertEqual(len(result), 1)
        self.client._get.assert_called_with("projects/1/merge_requests", params={'per_page': 100, 'page': 1})

    def test_get_project_pipelines(self):
        self.client._get.return_value.json.return_value = [{"id": 1}]
        result = list(self.client.get_project_pipelines(1))
        self.assertEqual(len(result), 1)
        self.client._get.assert_called_with("projects/1/pipelines", params={'per_page': 100, 'page': 1})

    def test_get_project_deployments(self):
        self.client._get.return_value.json.return_value = [{"id": 1}]
        result = list(self.client.get_project_deployments(1))
        self.assertEqual(len(result), 1)
        self.client._get.assert_called_with("projects/1/deployments", params={'per_page': 100, 'page': 1})

    def test_get_issue_notes(self):
        self.client._get.return_value.json.return_value = [{"id": 1}]
        result = list(self.client.get_issue_notes(1, 100))
        self.assertEqual(len(result), 1)
        self.client._get.assert_called_with("projects/1/issues/100/notes", params={'per_page': 100, 'page': 1})

    def test_get_mr_notes(self):
        self.client._get.return_value.json.return_value = [{"id": 1}]
        result = list(self.client.get_mr_notes(1, 100))
        self.assertEqual(len(result), 1)
        self.client._get.assert_called_with("projects/1/merge_requests/100/notes", params={'per_page': 100, 'page': 1})

    def test_get_project_tags(self):
        self.client._get.return_value.json.return_value = [{"name": "v1"}]
        result = list(self.client.get_project_tags(1))
        self.assertEqual(len(result), 1)
        self.client._get.assert_called_with("projects/1/repository/tags", params={'per_page': 100, 'page': 1})

    def test_get_project_branches(self):
        self.client._get.return_value.json.return_value = [{"name": "main"}]
        result = list(self.client.get_project_branches(1))
        self.assertEqual(len(result), 1)
        self.client._get.assert_called_with("projects/1/repository/branches", params={'per_page': 100, 'page': 1})

    def test_get_project_members(self):
        self.client._get.return_value.json.return_value = [{"username": "user1"}]
        result = list(self.client.get_project_members(1))
        self.assertEqual(len(result), 1)
        self.client._get.assert_called_with("projects/1/members/all", params={'per_page': 100, 'page': 1})

    def test_get_user(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 1, "username": "user1"}
        self.client._get.return_value = mock_resp
        
        user = self.client.get_user(1)
        self.assertEqual(user['username'], "user1")
        self.client._get.assert_called_with("users/1")

    def test_get_count(self):
        mock_resp = MagicMock()
        mock_resp.headers = {'x-total': '42'}
        self.client._get.return_value = mock_resp
        
        count = self.client.get_count("projects/1/issues")
        self.assertEqual(count, 42)
        
        args, kwargs = self.client._get.call_args
        self.assertEqual(kwargs['params']['per_page'], 1)

if __name__ == '__main__':
    unittest.main()

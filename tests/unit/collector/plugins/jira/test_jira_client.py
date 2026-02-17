"""TODO: Add module description."""
import unittest
from unittest.mock import patch, MagicMock
from devops_collector.plugins.jira.client import JiraClient

class TestJiraClient(unittest.TestCase):
    '''"""TODO: Add class description."""'''

    def setUp(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.base_url = 'https://jira.fake.com'
        self.client = JiraClient(self.base_url, 'test@mail.com', 'token')

    @patch('requests.get')
    def test_get_projects(self, mock_get):
        '''"""TODO: Add description.

Args:
    self: TODO
    mock_get: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [{'key': 'PROJ1', 'name': 'Project 1'}]
        projects = self.client.get_projects()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]['key'], 'PROJ1')

    @patch('requests.get')
    def test_get_issues_pagination(self, mock_get):
        '''"""TODO: Add description.

Args:
    self: TODO
    mock_get: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        mock_get.side_effect = [MagicMock(status_code=200, json=lambda: {'total': 3, 'issues': [{'id': '1', 'changelog': {'histories': []}}, {'id': '2'}]}), MagicMock(status_code=200, json=lambda: {'total': 3, 'issues': [{'id': '3'}]})]
        issues = self.client.get_issues('project = PROJ1')
        self.assertEqual(len(issues), 3)
        self.assertEqual(mock_get.call_count, 2)
if __name__ == '__main__':
    unittest.main()
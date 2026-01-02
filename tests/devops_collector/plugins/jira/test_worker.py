"""TODO: Add module description."""
import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base
from devops_collector.plugins.jira.worker import JiraWorker
from devops_collector.plugins.jira.models import JiraProject, JiraIssue, JiraIssueHistory
from devops_collector.models.base_models import Organization, User as GlobalUser

class TestJiraWorker(unittest.TestCase):
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
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.mock_client = MagicMock()
        self.worker = JiraWorker(self.session, self.mock_client)

    def tearDown(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.session.close()

    def test_process_task_new_project(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.mock_client._get.return_value = {'key': 'TEST', 'name': 'Test Project', 'description': 'Desc', 'lead': {'displayName': 'Project Lead'}}
        self.mock_client.get_boards.return_value = []
        self.mock_client.get_groups.return_value = [{'name': 'JiraDevs'}]
        self.mock_client.get_all_users.return_value = [{'accountId': 'jira_user_101', 'accountType': 'atlassian', 'displayName': 'Jira User', 'emailAddress': 'jira@fake.com', 'active': True}]
        self.mock_client.get_issues.return_value = [{'id': '101', 'key': 'TEST-1', 'fields': {'summary': 'Issue 1', 'status': {'name': 'Open'}, 'issuetype': {'name': 'Task'}, 'assignee': {'accountId': 'jira_user_101', 'displayName': 'Jira User', 'emailAddress': 'jira@fake.com'}, 'creator': {'accountId': 'user_creator', 'displayName': 'Creator X', 'emailAddress': 'creator@fake.com'}, 'reporter': {'accountId': 'user_reporter', 'displayName': 'Reporter Y', 'emailAddress': 'reporter@fake.com'}}, 'changelog': {'histories': [{'id': '1001', 'author': {'displayName': 'User A'}, 'created': '2024-01-01T10:00:00.000+0000', 'items': [{'field': 'status', 'fromString': 'New', 'toString': 'Open'}]}]}}]
        task = {'project_key': 'TEST'}
        self.worker.process_task(task)
        project = self.session.query(JiraProject).filter_by(key='TEST').first()
        self.assertIsNotNone(project)
        history = self.session.query(JiraIssueHistory).filter_by(issue_id='101').first()
        self.assertIsNotNone(history)
        self.assertEqual(project.lead_name, 'Project Lead')
        issue = self.session.query(JiraIssue).filter_by(id='101').first()
        self.assertEqual(issue.creator_name, 'Creator X')
        self.assertEqual(issue.reporter_name, 'Reporter Y')
        self.assertIsNotNone(issue.assignee_user_id)
        self.assertIsNotNone(issue.creator_user_id)
        self.assertIsNotNone(issue.reporter_user_id)
        org = self.session.query(Organization).filter_by(name='JiraDevs').first()
        self.assertIsNotNone(org)
        user = self.session.query(GlobalUser).filter_by(email='jira@fake.com').first()
        self.assertIsNotNone(user)
if __name__ == '__main__':
    unittest.main()
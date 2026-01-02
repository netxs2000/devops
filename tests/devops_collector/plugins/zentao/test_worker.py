"""TODO: Add module description."""
import unittest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base
from devops_collector.plugins.zentao.worker import ZenTaoWorker
from devops_collector.plugins.zentao.models import ZenTaoProduct, ZenTaoIssue, ZenTaoProductPlan, ZenTaoAction

class TestZenTaoWorker(unittest.TestCase):
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
        self.worker = ZenTaoWorker(self.session, self.mock_client)

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

    def test_process_task_full(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.mock_client._get.return_value = {'id': 1, 'name': 'Prod 1'}
        self.mock_client.get_plans.return_value = [{'id': 51, 'title': 'Plan A', 'openedBy': 'creator1', 'openedDate': '2024-01-01 09:00:00'}]
        self.mock_client.get_executions.return_value = []
        self.mock_client.get_departments.return_value = [{'id': 1, 'name': '研发部', 'parent': 0}]
        self.mock_client.get_users.return_value = [{'account': 'dev1', 'realname': '开发者1', 'dept': 1, 'dept_name': '研发部', 'email': 'dev1@fake.com'}]
        self.mock_client.get_stories.return_value = [{'id': 1001, 'title': 'Story 1', 'plan': 51, 'openedBy': 'dev1', 'assignedTo': 'dev1', 'openedDate': '2024-01-01 10:00:00'}]
        self.mock_client.get_test_cases.return_value = []
        self.mock_client.get_releases.return_value = []
        self.mock_client.get_actions.return_value = [{'id': 101, 'objectType': 'story', 'objectID': 1001, 'actor': 'dev1', 'action': 'opened', 'date': '2024-01-01 10:00:00'}]
        self.worker.process_task({'product_id': 1})
        prod = self.session.query(ZenTaoProduct).filter_by(id=1).first()
        self.assertIsNotNone(prod)
        action = self.session.query(ZenTaoAction).filter_by(id=101).first()
        self.assertIsNotNone(action)
        self.assertEqual(action.actor, 'dev1')
        plan = self.session.query(ZenTaoProductPlan).filter_by(id=51).first()
        self.assertIsNotNone(plan)
        self.assertEqual(plan.opened_by, 'creator1')
        issue = self.session.query(ZenTaoIssue).filter_by(id=1001).first()
        self.assertIsNotNone(issue)
        self.assertEqual(issue.opened_by, 'dev1')
        self.assertIsNotNone(issue.opened_by_user_id)
        self.assertIsNotNone(issue.assigned_to_user_id)
        self.assertEqual(issue.plan_id, 51)
        self.assertEqual(issue.title, 'Story 1')
if __name__ == '__main__':
    unittest.main()
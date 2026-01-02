"""TODO: Add module description."""
import unittest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, User, Organization
from devops_collector.plugins.gitlab.worker import UserResolver

class TestGitLabUserMapping(unittest.TestCase):
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
        self.resolver = UserResolver(self.session, self.mock_client)

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

    def test_skype_mapping(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.mock_client.get_user.return_value = {'id': 123, 'username': 'gitlab_user', 'name': 'GitLab User', 'email': 'user@example.com', 'skype': 'Cloud Department'}
        user_id = self.resolver.resolve(123)
        user = self.session.query(User).get(user_id)
        self.assertEqual(user.department, 'Cloud Department')
        org = self.session.query(Organization).get(user.organization_id)
        self.assertIsNotNone(org)
        self.assertEqual(org.name, 'Cloud Department')
        self.assertEqual(org.level, 'Center')
if __name__ == '__main__':
    unittest.main()
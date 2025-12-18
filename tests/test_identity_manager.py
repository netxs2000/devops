import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, User, IdentityMapping
from devops_collector.core.identity_manager import IdentityManager

class TestIdentityManager(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        self.session.close()

    def test_get_or_create_user_new(self):
        # Test creating a completely new user
        user = IdentityManager.get_or_create_user(
            self.session, 'jira', 'jira_user_1', 'user1@example.com', 'User One'
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'user1@example.com')
        
        # Verify mapping
        mapping = self.session.query(IdentityMapping).filter_by(source='jira', external_id='jira_user_1').first()
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.user_id, user.id)

    def test_identity_matching_by_email(self):
        # Create a user from Source A
        user_a = IdentityManager.get_or_create_user(
            self.session, 'jira', 'jira_acc', 'common@example.com', 'Jira Name'
        )
        
        # Sync from Source B with same email
        user_b = IdentityManager.get_or_create_user(
            self.session, 'zentao', 'zt_acc', 'common@example.com', 'ZenTao Name'
        )
        
        # Should be the same global user
        self.assertEqual(user_a.id, user_b.id)
        
        # Should have two mappings
        mappings = self.session.query(IdentityMapping).filter_by(user_id=user_a.id).all()
        self.assertEqual(len(mappings), 2)
        sources = [m.source for m in mappings]
        self.assertIn('jira', sources)
        self.assertIn('zentao', sources)

    def test_existing_mapping(self):
        # Create once
        IdentityManager.get_or_create_user(self.session, 'jira', 'acc1', 'u1@ex.com')
        # Get again
        user = IdentityManager.get_or_create_user(self.session, 'jira', 'acc1')
        
        self.assertEqual(user.email, 'u1@ex.com')

if __name__ == '__main__':
    unittest.main()

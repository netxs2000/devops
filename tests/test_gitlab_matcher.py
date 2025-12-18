import unittest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, User, IdentityMapping
from devops_collector.plugins.gitlab.worker import IdentityMatcher
from devops_collector.plugins.gitlab.models import Commit

class TestGitLabIdentityMatcher(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Setup test data
        # Create a global user
        self.user = User(username="jsmith", name="John Smith", email="john@example.com")
        self.session.add(self.user)
        self.session.flush()
        
        # Create a GitLab identity mapping for this user
        self.mapping = IdentityMapping(
            user_id=self.user.id,
            source='gitlab',
            external_id="jsmith_gl",     # GitLab username
            external_name="John S.",      # GitLab display name
            email="gl_john@example.com"   # GitLab email
        )
        self.session.add(self.mapping)
        self.session.commit()
        
        self.matcher = IdentityMatcher(self.session)

    def tearDown(self):
        self.session.close()

    def test_rule_1_email_match(self):
        # Rule 1: author_email == GitLab email
        commit = Commit(author_email="gl_john@example.com", author_name="Someone")
        user_id = self.matcher.match(commit)
        self.assertEqual(user_id, self.user.id)

    def test_rule_2_username_match(self):
        # Rule 2: author_name == GitLab username (external_id)
        commit = Commit(author_email="other@ex.com", author_name="jsmith_gl")
        user_id = self.matcher.match(commit)
        self.assertEqual(user_id, self.user.id)

    def test_rule_3_name_match(self):
        # Rule 3: author_name == GitLab name (external_name)
        commit = Commit(author_email="other@ex.com", author_name="John S.")
        user_id = self.matcher.match(commit)
        self.assertEqual(user_id, self.user.id)

    def test_rule_4_prefix_match(self):
        # Rule 4: author_email_prefix == GitLab username
        commit = Commit(author_email="jsmith_gl@company.com", author_name="Unknown")
        user_id = self.matcher.match(commit)
        self.assertEqual(user_id, self.user.id)

    def test_no_match_fallback(self):
        # Fallback: create new via IdentityManager
        commit = Commit(author_email="new@example.com", author_name="New User")
        user_id = self.matcher.match(commit)
        self.assertNotEqual(user_id, self.user.id)
        
        user = self.session.query(User).get(user_id)
        self.assertEqual(user.email, "new@example.com")

if __name__ == '__main__':
    unittest.main()

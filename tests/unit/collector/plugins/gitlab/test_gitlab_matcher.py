"""TODO: Add module description."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from devops_collector.models.base_models import Base, IdentityMapping, User
from devops_collector.plugins.gitlab.models import GitLabCommit as Commit
from devops_collector.plugins.gitlab.worker import IdentityMatcher


class TestGitLabIdentityMatcher(unittest.TestCase):
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
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.user = User(username="jsmith", full_name="John Smith", primary_email="john@example.com")
        self.session.add(self.user)
        self.session.flush()
        self.mapping = IdentityMapping(
            global_user_id=self.user.global_user_id,
            source_system="gitlab",
            external_user_id="jsmith_gl",
            external_username="John S.",
            external_email="gl_john@example.com",
        )
        self.session.add(self.mapping)
        self.session.commit()
        self.matcher = IdentityMatcher(self.session)

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

    def test_rule_1_email_match(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        commit = Commit(author_email="gl_john@example.com", author_name="Someone")
        user_id = self.matcher.match(commit)
        self.assertEqual(user_id, self.user.global_user_id)

    def test_rule_2_username_match(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        commit = Commit(author_email="other@ex.com", author_name="jsmith_gl")
        user_id = self.matcher.match(commit)
        self.assertEqual(user_id, self.user.global_user_id)

    def test_rule_3_name_match(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        commit = Commit(author_email="other@ex.com", author_name="John S.")
        user_id = self.matcher.match(commit)
        self.assertEqual(user_id, self.user.global_user_id)

    def test_rule_4_prefix_match(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        commit = Commit(author_email="jsmith_gl@company.com", author_name="Unknown")
        user_id = self.matcher.match(commit)
        self.assertEqual(user_id, self.user.global_user_id)

    def test_no_match_fallback(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        commit = Commit(author_email="new@example.com", author_name="New User")
        user_id = self.matcher.match(commit)
        self.assertIsNone(user_id)


if __name__ == "__main__":
    unittest.main()

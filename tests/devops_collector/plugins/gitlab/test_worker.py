
import unittest
from unittest.mock import MagicMock, patch, ANY, call
from datetime import datetime, timezone
import json

from devops_collector.plugins.gitlab.worker import GitLabWorker, DiffAnalyzer, IdentityMatcher, UserResolver
# Import models to use in assertions/setup, but we'll mock their usage in session
from devops_collector.models import Project, Commit, Issue, User, SyncLog

class TestDiffAnalyzer(unittest.TestCase):
    def test_get_comment_symbol(self):
        self.assertEqual(DiffAnalyzer.get_comment_symbol('test.py'), '#')
        self.assertEqual(DiffAnalyzer.get_comment_symbol('test.java'), '//')
        self.assertIsNone(DiffAnalyzer.get_comment_symbol('test.unknown'))

    def test_is_ignored(self):
        self.assertTrue(DiffAnalyzer.is_ignored('package-lock.json'))
        self.assertTrue(DiffAnalyzer.is_ignored('node_modules/lib.js'))
        self.assertFalse(DiffAnalyzer.is_ignored('src/start.py'))

    def test_analyze_diff(self):
        diff_text = """@@ -1,2 +1,3 @@
-old_line
+new_line
+# comment
+
"""
        # file_path is .py, so # is comment
        stats = DiffAnalyzer.analyze_diff(diff_text, 'test.py')
        
        # -old_line -> code_deleted = 1
        # +new_line -> code_added = 1
        # +# comment -> comment_added = 1
        # + (blank) -> blank_added = 1
        
        self.assertEqual(stats['code_deleted'], 1)
        self.assertEqual(stats['code_added'], 1)
        self.assertEqual(stats['comment_added'], 1)
        self.assertEqual(stats['blank_added'], 1)

class TestIdentityMatcher(unittest.TestCase):
    def test_match(self):
        # Mock session and users
        session = MagicMock()
        u1 = MagicMock(spec=User)
        u1.id = 1
        u1.email = "test@example.com"
        u1.name = "Test User"
        u1.username = "testuser"
        u1.public_email = None
        
        m1 = MagicMock()
        m1.source = 'gitlab'
        m1.user_id = 1
        m1.email = "test@example.com"
        m1.external_id = "testuser"
        m1.external_name = "Test User"
        
        session.query.return_value.filter_by.return_value.all.return_value = [m1]
        
        matcher = IdentityMatcher(session)
        
        # 1. Match by email
        c1 = MagicMock(spec=Commit)
        c1.author_email = "test@example.com"
        c1.author_name = "Anyone"
        self.assertEqual(matcher.match(c1), 1)
        
        # 2. Match by name
        c2 = MagicMock(spec=Commit)
        c2.author_email = "other@example.com"
        c2.author_name = "Test User"
        self.assertEqual(matcher.match(c2), 1)
        
        # 3. Match by username prefix in email
        c3 = MagicMock(spec=Commit)
        c3.author_email = "testuser@gmail.com"
        c3.author_name = "Anyone"
        self.assertEqual(matcher.match(c3), 1)
        
        # No match
        c4 = MagicMock(spec=Commit)
        c4.author_email = "unknown@example.com"
        c4.author_name = "Unknown"
        # Mock IdentityManager.get_or_create_user side effect
        with patch('devops_collector.plugins.gitlab.worker.IdentityManager.get_or_create_user') as mock_get_create:
            mock_get_create.return_value.id = 999
            self.assertEqual(matcher.match(c4), 999)

class TestUserResolver(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.client = MagicMock()
        self.resolver = UserResolver(self.session, self.client)

    def test_load_cache(self):
        # Already called in __init__
        # Test if it actually loaded query results
        self.session.query.return_value.filter_by.return_value.all.assert_called()

    def test_resolve_cached(self):
        self.resolver.cache[123] = 456
        self.assertEqual(self.resolver.resolve(123), 456)
        self.client.get_user.assert_not_called()

    def test_resolve_api_success(self):
        self.client.get_user.return_value = {
            "username": "newuser",
            "name": "New User",
            "email": "new@example.com"
        }
        
        # Mock session add
        new_user = MagicMock()
        new_user.id = 789
        
        # When User() is instantiated, we can't easily intercept it unless we mock the class.
        # But we can check if session.add was called.
        # To make it easier, let's just trust session interactions or mock User class if needed.
        # Here we just check side effects.
        
        # Mock IdentityManager.get_or_create_user side effect
        with patch('devops_collector.plugins.gitlab.worker.IdentityManager.get_or_create_user') as mock_get_create:
            mock_get_create.return_value.id = 789
            uid = self.resolver.resolve(999)
            
            self.assertEqual(uid, 789)
            self.client.get_user.assert_called_with(999)
            self.assertEqual(self.resolver.cache[999], 789)

    def test_resolve_api_failure(self):
        self.client.get_user.side_effect = Exception("API Error")
        uid = self.resolver.resolve(888)
        self.assertIsNone(uid)

class TestGitLabWorker(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.client = MagicMock()
        self.worker = GitLabWorker(self.session, self.client)

    def test_sync_project_success(self):
        self.client.get_project.return_value = {
            "id": 1,
            "name": "Test Repo",
            "path_with_namespace": "group/test-repo",
            "description": "Desc",
            "star_count": 10,
            "namespace": {"id": 10}
        }
        
        # Mock existing project query as None (new project)
        self.session.query.return_value.filter_by.return_value.first.return_value = None
        
        project = self.worker._sync_project(1)
        
        self.assertIsNotNone(project)
        self.assertEqual(project.id, 1)
        self.assertEqual(project.name, "Test Repo")
        self.session.add.assert_called_once()
        
    def test_sync_project_failure(self):
        self.client.get_project.side_effect = Exception("API Error")
        
        project = self.worker._sync_project(1)
        
        self.assertIsNone(project)

    def test_process_task_full(self):
        # Mock _sync_project to return a dummy project
        project = MagicMock(spec=Project)
        project.id = 1
        project.name = "Test"
        project.last_synced_at = None
        
        # Mock all internal sync methods to avoid complexity
        self.worker._sync_project = MagicMock(return_value=project)
        self.worker._sync_commits = MagicMock(return_value=10)
        self.worker._sync_issues = MagicMock(return_value=5)
        self.worker._sync_merge_requests = MagicMock(return_value=2)
        self.worker._sync_pipelines = MagicMock(return_value=0)
        self.worker._sync_deployments = MagicMock(return_value=0)
        self.worker._sync_tags = MagicMock(return_value=0)
        self.worker._sync_branches = MagicMock(return_value=0)
        self.worker._match_identities = MagicMock()
        
        task = {
            "source": "gitlab",
            "project_id": 1,
            "job_type": "full"
        }
        
        self.worker.process_task(task)
        
        # Verify sync methods called
        self.worker._sync_project.assert_called_with(1)
        self.worker._sync_commits.assert_called_with(project, None)
        
        # Verify project status update
        self.assertEqual(project.sync_status, "COMPLETED")
        
        # Verify log added
        self.session.add.assert_called() # one for SyncLog
        self.session.commit.assert_called()

    def test_save_commits_batch(self):
        project = MagicMock(spec=Project)
        project.id = 1
        
        batch = [
            {
                "id": "sha1",
                "short_id": "s1",
                "title": "Initial commit",
                "author_name": "Test User",
                "author_email": "test@example.com",
                "message": "Commit message",
                "authored_date": "2023-01-01T12:00:00Z",
                "committed_date": "2023-01-01T12:00:00Z"
            }
        ]
        
        # Mock existing commits query
        self.session.query.return_value.filter.return_value.all.return_value = []
        
        self.worker._save_commits_batch(project, batch)
        
        # Verify commit added
        self.session.add.assert_called()
        args, _ = self.session.add.call_args
        commit = args[0]
        self.assertIsInstance(commit, Commit)
        self.assertEqual(commit.id, "sha1")

    def test_save_issues_batch(self):
        project = MagicMock(spec=Project)
        project.id = 1
        batch = [{"id": 101, "iid": 1, "title": "Bug", "state": "opened", "created_at": "2023-01-01T12:00:00Z", "updated_at": "2023-01-01T12:00:00Z"}]
        self.session.query.return_value.filter.return_value.all.return_value = []
        
        self.worker._save_issues_batch(project, batch)
        
        self.session.add.assert_called()
        issue = self.session.add.call_args[0][0]
        self.assertIsInstance(issue, Issue)
        self.assertEqual(issue.title, "Bug")

    def test_save_mrs_batch(self):
        project = MagicMock(spec=Project)
        project.id = 1
        batch = [{"id": 201, "iid": 1, "title": "Feature", "state": "opened", "created_at": "2023-01-01T12:00:00Z", "updated_at": "2023-01-01T12:00:00Z"}]
        self.session.query.return_value.filter.return_value.all.return_value = []
        
        self.worker._save_mrs_batch(project, batch)
        self.session.add.assert_called()

    def test_save_pipelines_batch(self):
        project = MagicMock(spec=Project)
        project.id = 1
        batch = [{"id": 301, "status": "success", "created_at": "2023-01-01T12:00:00Z", "updated_at": "2023-01-01T12:00:00Z"}]
        self.session.query.return_value.filter.return_value.all.return_value = []
        
        self.worker._save_pipelines_batch(project, batch)
        self.session.add.assert_called()

    def test_save_deployments_batch(self):
        project = MagicMock(spec=Project)
        project.id = 1
        batch = [{"id": 401, "status": "success", "iid": 1, "created_at": "2023-01-01T12:00:00Z", "updated_at": "2023-01-01T12:00:00Z"}]
        self.session.query.return_value.filter.return_value.all.return_value = []
        
        self.worker._save_deployments_batch(project, batch)
        self.session.add.assert_called()

    def test_save_tags_batch(self):
        project = MagicMock(spec=Project)
        project.id = 1
        batch = [{"name": "v1.0"}]
        self.session.query.return_value.filter.return_value.all.return_value = []
        
        self.worker._save_tags_batch(project, batch)
        self.session.add.assert_called()

    def test_save_branches_batch(self):
        project = MagicMock(spec=Project)
        project.id = 1
        batch = [{"name": "main"}]
        self.session.query.return_value.filter.return_value.all.return_value = []
        
        self.worker._save_branches_batch(project, batch)
        self.session.add.assert_called()

    def test_match_identities(self):
        project = MagicMock(spec=Project)
        project.id = 1
        
        # Mock unlinked commits
        c1 = MagicMock(spec=Commit)
        c1.gitlab_user_id = None
        self.session.query.return_value.filter_by.return_value.all.return_value = [c1]
        
        # Mock IdentityMatcher
        with patch('devops_collector.plugins.gitlab.worker.IdentityMatcher') as MockMatcher:
            matcher_instance = MockMatcher.return_value
            matcher_instance.match.return_value = 999
            
            self.worker._match_identities(project)
            
            self.assertEqual(c1.gitlab_user_id, 999)
            self.session.commit.assert_called()

    def test_process_generator(self):
        # Generator yielding 5 items
        def gen():
            for i in range(5):
                yield i
        
        processor = MagicMock()
        
        # Batch size 2 -> should call processor 3 times: [0,1], [2,3], [4]
        count = self.worker._process_generator(gen(), processor, batch_size=2)
        
        self.assertEqual(count, 5)
        self.assertEqual(processor.call_count, 3)
        processor.assert_has_calls([
            call([0, 1]),
            call([2, 3]),
            call([4])
        ])
        
        # Check commits
        self.assertEqual(self.session.commit.call_count, 3)

    def test_process_generator_error(self):
        def gen():
            yield 1
            
        processor = MagicMock(side_effect=Exception("DB Error"))
        
        with self.assertRaises(Exception):
            self.worker._process_generator(gen(), processor, batch_size=1)
            
        self.session.rollback.assert_called()

if __name__ == '__main__':
    unittest.main()

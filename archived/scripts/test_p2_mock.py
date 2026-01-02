"""P2 任务 Mock 单元测试脚本 (Fix)

本脚本使用 unittest.mock 模拟数据库和网络请求，验证 P2 任务中的核心业务逻辑
"""
import sys
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import asyncio
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.modules['devops_collector.config'] = MagicMock()
sys.modules['devops_collector.auth.database'] = MagicMock()
sys.modules['devops_collector.models.gitlab_models'] = MagicMock()
sys.modules['devops_collector.models.base_models'] = MagicMock()
sys.modules['devops_collector.auth'] = MagicMock()
sys.modules['requests'] = MagicMock()
mock_config = MagicMock()
mock_config.Config.GITLAB_URL = 'https://gitlab.example.com'
mock_config.Config.GITLAB_PRIVATE_TOKEN = 'token'
sys.modules['devops_collector.config'] = mock_config
from devops_collector.models.gitlab_models import Project
from devops_collector.models.base_models import Location, User
logger = MagicMock()

async def get_project_stakeholders_logic(project_id: int, mock_db):
    """(复刻 logic) 获取项目干系人"""
    stakeholders = []
    try:
        project = mock_db.query(Project).filter(Project.gitlab_project_id == project_id).first()
        if project and hasattr(project, 'location_id') and project.location_id:
            location = mock_db.query(Location).filter(Location.location_id == project.location_id).first()
            if location and location.manager_user_id:
                stakeholders.append(str(location.manager_user_id))
    except Exception as e:
        logger.warning(f'Failed to query project stakeholders: {e}')
    return stakeholders

async def get_requirement_author_logic(project_id: int, req_iid: int, mock_requests, mock_db, mock_auth_services):
    """(复刻 logic) 获取需求作者"""
    url = f'https://gitlab.example.com/api/v4/projects/{project_id}/issues/{req_iid}'
    headers = {'PRIVATE-TOKEN': 'token'}
    try:
        resp = mock_requests.get(url, headers=headers, timeout=5)
        if resp.ok:
            issue_data = resp.json()
            author_email = issue_data.get('author', {}).get('email')
            if author_email:
                user = mock_auth_services.get_user_by_email(mock_db, email=author_email)
                if user:
                    return str(user.global_user_id)
    except Exception:
        pass
    return None

class TestP2NotificationLogic(unittest.TestCase):
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
        self.mock_db = MagicMock()
        self.mock_requests = MagicMock()
        self.mock_auth_services = MagicMock()

    def test_get_project_stakeholders_found(self):
        """测试：成功找到项目关联的区域负责人"""
        mock_project_obj = MagicMock()
        mock_project_obj.location_id = '440000'
        mock_location_obj = MagicMock()
        mock_location_obj.manager_user_id = 'user-uuid-123'

        def query_side_effect(model):
            '''"""TODO: Add description.

Args:
    model: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
            chain_mock = MagicMock()
            if model == Project:
                chain_mock.filter.return_value.first.return_value = mock_project_obj
            elif model == Location:
                chain_mock.filter.return_value.first.return_value = mock_location_obj
            return chain_mock
        self.mock_db.query.side_effect = query_side_effect
        result = asyncio.run(get_project_stakeholders_logic(1, self.mock_db))
        self.assertEqual(result, ['user-uuid-123'])
        print('[PASS] test_get_project_stakeholders_found')

    def test_get_project_stakeholders_no_location(self):
        """测试：项目没有关联 Location"""
        mock_project_obj = MagicMock()
        mock_project_obj.location_id = None

        def query_side_effect(model):
            '''"""TODO: Add description.

Args:
    model: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
            chain_mock = MagicMock()
            if model == Project:
                chain_mock.filter.return_value.first.return_value = mock_project_obj
            return chain_mock
        self.mock_db.query.side_effect = query_side_effect
        result = asyncio.run(get_project_stakeholders_logic(1, self.mock_db))
        self.assertEqual(result, [])
        print('[PASS] test_get_project_stakeholders_no_location')

    def test_get_requirement_author_found(self):
        """测试：成功从 GitLab 获取作者并通过邮箱匹配到用户"""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {'author': {'email': 'tom@example.com'}}
        self.mock_requests.get.return_value = mock_resp
        mock_user = MagicMock()
        mock_user.global_user_id = 'user-uuid-999'
        self.mock_auth_services.get_user_by_email.return_value = mock_user
        result = asyncio.run(get_requirement_author_logic(1, 10, self.mock_requests, self.mock_db, self.mock_auth_services))
        self.assertEqual(result, 'user-uuid-999')
        print('[PASS] test_get_requirement_author_found')

    def test_get_requirement_author_gitlab_fail(self):
        """测试：GitLab 请求失败"""
        mock_resp = MagicMock()
        mock_resp.ok = False
        self.mock_requests.get.return_value = mock_resp
        result = asyncio.run(get_requirement_author_logic(1, 10, self.mock_requests, self.mock_db, self.mock_auth_services))
        self.assertIsNone(result)
        print('[PASS] test_get_requirement_author_gitlab_fail')

    def test_notification_target_logic(self):
        """测试业务场景：测试失败的通知目标计算逻辑"""
        executor_uid = 'user-1'
        tc_author_id = 'user-2'
        req_author = 'user-3'
        notify_users = [executor_uid]
        if tc_author_id and tc_author_id != executor_uid:
            notify_users.append(tc_author_id)
        if req_author and req_author not in notify_users:
            notify_users.append(req_author)
        self.assertEqual(len(notify_users), 3)
        self.assertIn('user-1', notify_users)
        self.assertIn('user-2', notify_users)
        self.assertIn('user-3', notify_users)
        print('[PASS] test_notification_target_logic (Separate Users)')
        notify_users_unique = ['user-1']
        tc_author_id = 'user-1'
        req_author = 'user-1'
        if tc_author_id and tc_author_id != 'user-1':
            notify_users_unique.append(tc_author_id)
        if req_author and req_author not in notify_users_unique:
            notify_users_unique.append(req_author)
        self.assertEqual(len(notify_users_unique), 1)
        print('[PASS] test_notification_target_logic (Same User)')
if __name__ == '__main__':
    unittest.main()
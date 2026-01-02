"""单元测试：BaseClient

验证 API 客户端的重试机制、错误处理和限流集成。
"""
import unittest
from unittest.mock import patch, MagicMock
import requests
from devops_collector.core.base_client import BaseClient

class MockClient(BaseClient):
    """用于测试的 BaseClient 实现类。"""

    def test_connection(self) -> bool:
        """实现抽象方法。"""
        return True

class TestBaseClient(unittest.TestCase):
    """BaseClient 重试与错误处理测试类。"""

    def setUp(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.client = MockClient(base_url='http://api.example.com', auth_headers={'Authorization': 'Bearer token'}, rate_limit=100)

    @patch('requests.get')
    def test_get_success(self, mock_get):
        """测试普通的 GET 请求。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        response = self.client._get('test-endpoint')
        self.assertEqual(response.status_code, 200)
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_retry_on_429(self, mock_get):
        """测试遇到 429 速率限制时的重试行为。"""
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {'Retry-After': '0'}
        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_get.side_effect = [mock_429, mock_200]
        response = self.client._get('test-endpoint')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_get.call_count, 2)

    @patch('requests.get')
    def test_no_retry_on_401(self, mock_get):
        """测试遇到 401 认证错误时立即报错，不重试。"""
        mock_401 = MagicMock()
        mock_401.status_code = 401
        mock_401.raise_for_status.side_effect = requests.exceptions.HTTPError('Unauthorized', response=mock_401)
        mock_get.return_value = mock_401
        with self.assertRaises(requests.exceptions.HTTPError):
            self.client._get('test-endpoint')
        self.assertEqual(mock_get.call_count, 1)
if __name__ == '__main__':
    unittest.main()
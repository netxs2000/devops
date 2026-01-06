"""PyAirbyte GitLab 集成单元测试（纯 Mock 适配版）。

本测试通过完全 Mock 外部依赖，验证 AirbyteGitLabClient 的数据转换逻辑。
"""

import unittest
from unittest.mock import MagicMock, patch

class TestPyAirbyteGitLabIntegration(unittest.TestCase):
    """测试 PyAirbyte 数据适配逻辑。"""

    @patch("airbyte.get_source")
    def test_airbyte_client_stream_records(self, mock_get_source):
        """测试 AirbyteGitLabClient 是否能正确转换流记录。"""
        # 手动导入，避免顶层循环
        from devops_collector.plugins.gitlab.airbyte_client import AirbyteGitLabClient

        # 1. 模拟 Airbyte 返回的记录
        mock_source = MagicMock()
        mock_get_source.return_value = mock_source
        
        mock_record = MagicMock()
        mock_record.to_dict.return_value = {
            "id": "sha-123",
            "project_id": 456,
            "title": "Test Commit",
            "author_name": "Antigravity"
        }
        
        mock_read_result = MagicMock()
        # 兼容 dict 风格访问
        mock_read_result.__getitem__.side_effect = lambda key: [mock_record] if key == "commits" else []
        mock_source.read.return_value = mock_read_result

        # 2. 执行测试
        client = AirbyteGitLabClient(url="https://mock.com", token="token")
        records = list(client.get_stream_records("commits"))

        # 3. 验证
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "sha-123")
        self.assertEqual(records[0]["author_name"], "Antigravity")
        mock_source.select_streams.assert_called_with(["commits"])

if __name__ == "__main__":
    unittest.main()

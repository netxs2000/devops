"""PyAirbyte SonarQube 集成单元测试 (修复导入版)。

验证 AirbyteSonarQubeClient 的适配逻辑。
"""

import unittest
from unittest.mock import MagicMock, patch

class TestPyAirbyteSonarQubeIntegration(unittest.TestCase):
    """测试 SonarQube 在 Airbyte 模式下的适配。"""

    @patch("airbyte.get_source")
    def test_airbyte_client_get_measures(self, mock_get_source):
        """测试适配器是否能正确解析指标数据。"""
        from devops_collector.plugins.sonarqube.airbyte_client import AirbyteSonarQubeClient

        # 1. 模拟记录
        mock_source = MagicMock()
        mock_get_source.return_value = mock_source
        
        mock_m1 = MagicMock()
        mock_m1.to_dict.return_value = {"componentKey": "prj-1", "metric": "coverage", "value": "85.0"}
        mock_m2 = MagicMock()
        mock_m2.to_dict.return_value = {"componentKey": "prj-1", "metric": "bugs", "value": "10"}
        
        mock_read_result = MagicMock()
        mock_read_result.__getitem__.side_effect = lambda key: [mock_m1, mock_m2] if key == "measures" else []
        mock_source.read.return_value = mock_read_result

        # 2. 执行
        client = AirbyteSonarQubeClient(url="https://sonar.mock", token="token")
        measures = client.get_measures("prj-1")

        # 3. 验证
        self.assertEqual(measures["coverage"], "85.0")
        self.assertEqual(measures["bugs"], "10")

if __name__ == "__main__":
    unittest.main()

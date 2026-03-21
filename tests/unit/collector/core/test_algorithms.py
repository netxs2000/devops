"""核心算法工具类单元测试 (algorithms.py)"""

import unittest
from datetime import UTC, datetime

from devops_collector.core.algorithms import AgileMetrics, CodeMetrics, QualityMetrics


class TestAgileMetrics(unittest.TestCase):
    """测试敏捷指标计算逻辑。"""

    def test_calculate_cycle_time(self):
        """测试周期时间计算。"""
        start = datetime(2025, 12, 1, 10, 0, 0, tzinfo=UTC)
        mid = datetime(2025, 12, 1, 14, 0, 0, tzinfo=UTC)
        end = datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC)
        histories = [
            {"to_string": "In Progress", "created_at": start},
            {"to_string": "Testing", "created_at": mid},
            {"to_string": "Done", "created_at": end},
        ]
        cycle_time = AgileMetrics.calculate_cycle_time(histories)
        self.assertEqual(cycle_time, 24.0)

    def test_calculate_cycle_time_reopen(self):
        """测试重开场景下的周期时间。"""
        t1 = datetime(2025, 12, 1, 10, 0, tzinfo=UTC)
        t2 = datetime(2025, 12, 1, 12, 0, tzinfo=UTC)
        t3 = datetime(2025, 12, 1, 14, 0, tzinfo=UTC)
        t4 = datetime(2025, 12, 1, 16, 0, tzinfo=UTC)
        histories = [
            {"to_string": "In Progress", "created_at": t1},
            {"to_string": "Done", "created_at": t2},
            {"to_string": "In Progress", "created_at": t3},
            {"to_string": "Done", "created_at": t4},
        ]
        cycle_time = AgileMetrics.calculate_cycle_time(histories)
        self.assertEqual(cycle_time, 6.0)



class TestCodeMetrics(unittest.TestCase):
    """测试代码度量算法。"""

    def test_analyze_diff_python(self):
        """测试 Python 代码 Diff 分析。"""
        diff = "+def hello():\n+# This is a comment\n+    print('world')\n-old_line\n+ \n"
        stats = CodeMetrics.analyze_diff(diff, "test.py")
        self.assertEqual(stats["code_added"], 2)
        self.assertEqual(stats["comment_added"], 1)
        self.assertEqual(stats["blank_added"], 1)
        self.assertEqual(stats["code_deleted"], 1)

    def test_get_file_category(self):
        """测试文件分类。"""
        self.assertEqual(CodeMetrics.get_file_category("src/main.py"), "Code")
        self.assertEqual(CodeMetrics.get_file_category("tests/test_api.py"), "Test")
        self.assertEqual(CodeMetrics.get_file_category("deploy/docker-compose.yml"), "IaC")
        self.assertEqual(CodeMetrics.get_file_category("config/settings.ini"), "Config")


class TestQualityMetrics(unittest.TestCase):
    """测试质量指标转换。"""

    def test_rating_to_letter(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        self.assertEqual(QualityMetrics.rating_to_letter("1.0"), "A")
        self.assertEqual(QualityMetrics.rating_to_letter(2.0), "B")
        self.assertEqual(QualityMetrics.rating_to_letter("5.0"), "E")
        self.assertEqual(QualityMetrics.rating_to_letter("unknown"), "E")


if __name__ == "__main__":
    unittest.main()

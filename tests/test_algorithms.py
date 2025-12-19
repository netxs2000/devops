"""核心算法工具类单元测试 (algorithms.py)"""
import unittest
from datetime import datetime, timezone, timedelta
from devops_collector.core.algorithms import AgileMetrics, CodeMetrics, QualityMetrics

class TestAgileMetrics(unittest.TestCase):
    """测试敏捷指标计算逻辑。"""

    def test_calculate_cycle_time(self):
        """测试周期时间计算。"""
        start = datetime(2025, 12, 1, 10, 0, 0, tzinfo=timezone.utc)
        mid = datetime(2025, 12, 1, 14, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 2, 10, 0, 0, tzinfo=timezone.utc)
        
        histories = [
            {'to_string': 'In Progress', 'created_at': start},
            {'to_string': 'Testing', 'created_at': mid},
            {'to_string': 'Done', 'created_at': end}
        ]
        
        # 10:00 (1st Dec) to 10:00 (2nd Dec) = 24 hours
        cycle_time = AgileMetrics.calculate_cycle_time(histories)
        self.assertEqual(cycle_time, 24.0)

    def test_calculate_cycle_time_reopen(self):
        """测试重开场景下的周期时间。"""
        t1 = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2025, 12, 1, 12, 0, tzinfo=timezone.utc)
        t3 = datetime(2025, 12, 1, 14, 0, tzinfo=timezone.utc)
        t4 = datetime(2025, 12, 1, 16, 0, tzinfo=timezone.utc)
        
        histories = [
            {'to_string': 'In Progress', 'created_at': t1},
            {'to_string': 'Done', 'created_at': t2},
            {'to_string': 'In Progress', 'created_at': t3},
            {'to_string': 'Done', 'created_at': t4}
        ]
        # First In Progress (t1) to Last Done (t4) = 6 hours
        cycle_time = AgileMetrics.calculate_cycle_time(histories)
        self.assertEqual(cycle_time, 6.0)

    def test_calculate_lead_time(self):
        """测试前置时间计算。"""
        created = datetime(2025, 12, 1, 10, 0, tzinfo=timezone.utc)
        resolved = datetime(2025, 12, 1, 12, 30, tzinfo=timezone.utc)
        
        lead_time = AgileMetrics.calculate_lead_time(created, resolved)
        self.assertEqual(lead_time, 2.5)

class TestCodeMetrics(unittest.TestCase):
    """测试代码度量算法。"""

    def test_analyze_diff_python(self):
        """测试 Python 代码 Diff 分析。"""
        diff = "+def hello():\n+# This is a comment\n+    print('world')\n-old_line\n+ \n"
        stats = CodeMetrics.analyze_diff(diff, "test.py")
        
        self.assertEqual(stats['code_added'], 2)  # def hello, print
        self.assertEqual(stats['comment_added'], 1) # This is a comment
        self.assertEqual(stats['blank_added'], 1)   # space line
        self.assertEqual(stats['code_deleted'], 1)

    def test_get_file_category(self):
        """测试文件分类。"""
        self.assertEqual(CodeMetrics.get_file_category("src/main.py"), "Code")
        self.assertEqual(CodeMetrics.get_file_category("tests/test_api.py"), "Test")
        self.assertEqual(CodeMetrics.get_file_category("deploy/docker-compose.yml"), "IaC")
        self.assertEqual(CodeMetrics.get_file_category("config/settings.ini"), "Config")

class TestQualityMetrics(unittest.TestCase):
    """测试质量指标转换。"""

    def test_rating_to_letter(self):
        self.assertEqual(QualityMetrics.rating_to_letter("1.0"), "A")
        self.assertEqual(QualityMetrics.rating_to_letter(2.0), "B")
        self.assertEqual(QualityMetrics.rating_to_letter("5.0"), "E")
        self.assertEqual(QualityMetrics.rating_to_letter("unknown"), "E")

if __name__ == "__main__":
    unittest.main()

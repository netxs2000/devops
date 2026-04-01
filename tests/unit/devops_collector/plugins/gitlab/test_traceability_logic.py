import unittest
from unittest.mock import MagicMock

from devops_collector.models.base_models import TraceabilityLink
from devops_collector.plugins.gitlab.mixins.traceability_mixin import TraceabilityMixin
from devops_collector.plugins.gitlab.models import GitLabMergeRequest


class MockWorker(TraceabilityMixin):
    def __init__(self, session):
        self.session = session


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from devops_collector.models.base_models import Base


class TestTraceabilityExtraction(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.worker = MockWorker(self.session)

    def tearDown(self):
        self.session.close()

    def test_extract_zentao_ids_standard_format(self):
        """测试标准 #123 格式提取"""
        mr = MagicMock(spec=GitLabMergeRequest)
        mr.title = "实现财务逻辑 #120"
        mr.description = "修复了结算 Bug #121"
        mr.external_issue_id = None
        mr.id = 101
        mr.iid = 1

        self.worker._apply_traceability_extraction(mr)

        # 验证 MR 对象的主字段 (仅存第一个)
        self.assertEqual(mr.external_issue_id, "120")
        self.assertEqual(mr.issue_source, "zentao")

        # 验证追溯表记录 (保存全部)
        added_links = self.session.query(TraceabilityLink).all()
        self.assertEqual(len(added_links), 2)

        source_ids = [link.source_id for link in added_links]
        self.assertIn("120", source_ids)
        self.assertIn("121", source_ids)

        # 验证是否标记为初步关联
        for link in added_links:
            self.assertTrue(link.raw_data.get("is_tentative"))

    def test_multiple_ids_order(self):
        """测试多个 ID 顺序及唯一性"""
        mr = MagicMock(spec=GitLabMergeRequest)
        mr.title = "需求 #101 #102 #101"  # 重复 ID
        mr.description = ""
        mr.external_issue_id = None
        mr.iid = 5

        self.worker._apply_traceability_extraction(mr)

        # 主字段应为第一个 101
        self.assertEqual(mr.external_issue_id, "101")

        # 追溯表应只有 101 和 102，且没有重复
        added_links = self.session.query(TraceabilityLink).all()
        added_ids = [link.source_id for link in added_links]
        self.assertEqual(len(set(added_ids)), 2)
        self.assertEqual(sorted(added_ids), ["101", "102"])

    def test_negative_matching(self):
        """测试负向匹配，不应匹配到 C# 或单词内含 # 的情况"""
        mr = MagicMock(spec=GitLabMergeRequest)
        mr.title = "C# 语法更新及 #A123 错误格式"
        mr.description = "正确格式在最后 #999"
        mr.external_issue_id = None

        self.worker._apply_traceability_extraction(mr)

        # 应该只匹配到 999
        self.assertEqual(mr.external_issue_id, "999")

        added_links = self.session.query(TraceabilityLink).all()
        self.assertEqual(len(added_links), 1)
        self.assertEqual(added_links[0].source_id, "999")


if __name__ == "__main__":
    unittest.main()

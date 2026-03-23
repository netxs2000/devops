import unittest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from devops_collector.models.base_models import Base
from devops_collector.plugins.zentao.models import ZenTaoIssue, ZenTaoProduct
from devops_collector.plugins.zentao.worker import ZenTaoWorker


class TestZenTaoSyncLogic(unittest.TestCase):
    def setUp(self):
        # 使用内存数据库进行测试
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.client = MagicMock()
        self.worker = ZenTaoWorker(self.session, self.client)

        # 预置种子数据以满足外键约束
        self.product = ZenTaoProduct(id=1, name="Test Product")
        self.session.add(self.product)
        self.session.commit()

    def tearDown(self):
        self.session.close()

    def test_transform_task_with_effort(self):
        """验证任务工时转换逻辑 (FinOps 核心)"""
        product_id = 1
        execution_id = 101
        from devops_collector.plugins.zentao.models import ZenTaoExecution
        execution = ZenTaoExecution(id=101, product_id=product_id, name="Test Execution")
        self.session.add(execution)
        self.session.flush()

        task_data = {
            "id": 500,
            "name": "编写单元测试",
            "status": "doing",
            "pri": 1,
            "type": "devel",
            "estimate": 5.5,
            "consumed": 2.0,
            "left": 3.5,
        }

        # 执行转换
        issue = self.worker._transform_task(product_id, execution_id, task_data)

        self.assertEqual(issue.id, 500)
        self.assertEqual(issue.type, "task")
        self.assertEqual(issue.estimate, "5.5")
        self.assertEqual(issue.consumed, "2.0")
        self.assertEqual(issue.left, "3.5")
        self.assertEqual(issue.task_type, "devel")

    def test_composite_primary_key(self):
        """验证联合主键 (id, type) 是否生效，防止 ID 冲突"""
        # 创建一个 ID 为 1000 的需求 (feature)
        issue_f = ZenTaoIssue(id=1000, type="feature", title="需求A", product_id=1)
        self.session.add(issue_f)

        # 创建一个同样 ID 为 1000 的任务 (task)
        issue_t = ZenTaoIssue(id=1000, type="task", title="任务A", product_id=1)
        self.session.add(issue_t)

        # 如果主键设置正确，这里不应该报错
        self.session.commit()

        count = self.session.query(ZenTaoIssue).filter_by(id=1000).count()
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()

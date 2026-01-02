"""SQL View 指标校验测试框架 (Metric Validation Framework)

该模块提供了一个自动化的测试底座，用于验证核心分析指标 (DORA, ROI, Cycle Time 等) 
在 SQL View 层的逻辑正确性。

核心理念:
1. 隔离性: 每个测试用例在独立的临时 Schema 中运行。
2. 确定性: 使用预定义的“黄金数据集 (Golden Dataset)”。
3. 声明式: 通过预期结果 JSON 声明校验逻辑。
"""
import os
import unittest
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base

class MetricValidatorFramework(unittest.TestCase):
    """SQL 指标校验基类。"""
    DB_URL = 'postgresql://postgres:postgres@localhost:5432/devops_test'
    SQL_VIEWS_DIR = 'devops_collector/plugins/gitlab/sql_views'

    @classmethod
    def setUpClass(cls):
        """初始化测试数据库连接并创建基础架构。"""
        try:
            cls.engine = create_engine(cls.DB_URL)
            with cls.engine.connect() as conn:
                conn.execute(text('CREATE SCHEMA IF NOT EXISTS test_analytics;'))
                conn.execute(text('SET search_path TO test_analytics, public;'))
                conn.commit()
            Base.metadata.create_all(cls.engine)
            cls.Session = sessionmaker(bind=cls.engine)
        except Exception as e:
            raise unittest.SkipTest(f'无法连接测试数据库: {e}')

    def setUp(self):
        """单次测试前的准备工作：清空数据并加载 View。"""
        self.session = self.Session()
        self._clear_data()

    def tearDown(self):
        """测试后清理。"""
        self.session.rollback()
        self.session.close()

    def _clear_data(self):
        """递归清空测试 Schema 中的所有数据。"""
        meta = Base.metadata
        for table in reversed(meta.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()

    def deploy_view(self, view_filename: str):
        """从文件系统加载并执行 SQL View 定义。
        
        Args:
            view_filename: SQL 文件名 (如 'dora_metrics.sql')
        """
        possible_paths = [os.path.join(self.SQL_VIEWS_DIR, view_filename), os.path.join('devops_collector/sql', view_filename)]
        sql_content = None
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                break
        if not sql_content:
            raise FileNotFoundError(f'未找到 SQL 视图文件: {view_filename}')
        with self.engine.connect() as conn:
            conn.execute(text('SET search_path TO test_analytics, public;'))
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()

    def insert_golden_data(self, models: List[Any]):
        """插入黄金数据集。"""
        self.session.add_all(models)
        self.session.commit()

    def assert_view_results(self, view_name: str, expected_data: List[Dict[str, Any]], key_fields: List[str]=None):
        """执行 View 查询并比对结果。
        
        Args:
            view_name: 视图名称。
            expected_data: 预期的数据行列表。
            key_fields: 用于排序和定位的关键字。
        """
        query = text(f'SELECT * FROM test_analytics.{view_name}')
        result = self.session.execute(query)
        actual_data = [dict(row._mapping) for row in result]
        if key_fields:
            actual_data.sort(key=lambda x: [x.get(f) for f in key_fields])
            expected_data.sort(key=lambda x: [x.get(f) for f in key_fields])
        self.assertEqual(len(actual_data), len(expected_data), f'结果行数不匹配！实际: {len(actual_data)}, 预期: {len(expected_data)}')
        for i, (actual, expected) in enumerate(zip(actual_data, expected_data)):
            for field, expected_val in expected.items():
                actual_val = actual.get(field)
                self.assertEqual(actual_val, expected_val, f"第 {i} 行字段 '{field}' 不匹配！实际: {actual_val}, 预期: {expected_val}")
from devops_collector.plugins.gitlab.models import Deployment, MergeRequest, Commit
from datetime import datetime, timedelta

class TestDoraMetrics(MetricValidatorFramework):
    """针对 DORA 指标视图的专项验证。"""

    def test_deployment_frequency(self):
        """验证部署频率计算逻辑。"""
        today = datetime.now()
        data = [Deployment(project_id=101, status='success', environment='prod', created_at=today), Deployment(project_id=101, status='success', environment='prod', created_at=today - timedelta(hours=1)), Deployment(project_id=101, status='failed', environment='prod', created_at=today - timedelta(hours=2)), Deployment(project_id=102, status='success', environment='prod', created_at=today - timedelta(days=365))]
        self.insert_golden_data(data)
        self.deploy_view('dora_metrics.sql')
        expected = [{'project_id': 101, 'successful_deployments': 2, 'deployment_date': today.replace(hour=0, minute=0, second=0, microsecond=0)}]
        self.assert_view_results('dora_deployment_frequency', expected, key_fields=['project_id'])
if __name__ == '__main__':
    unittest.main()
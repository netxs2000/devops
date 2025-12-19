import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from devops_collector.models.base_models import Base, OKRObjective, OKRKeyResult
from devops_collector.models import Commit, Project
from devops_collector.plugins.sonarqube.models import SonarMeasure
from devops_collector.core.okr_service import OKRService

class TestOKRService(unittest.TestCase):
    """OKR 自动化服务单元测试。"""

    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.service = OKRService(self.session)

    def tearDown(self):
        self.session.close()

    def test_update_sonar_metric(self):
        """测试 Sonar 指标自动更新。"""
        # 1. 准备目标数据
        obj = OKRObjective(title="提升代码质量", status="active")
        self.session.add(obj)
        self.session.flush()

        kr = OKRKeyResult(
            objective_id=obj.id,
            title="单测覆盖率达到 80%",
            initial_value="50",
            target_value="80",
            current_value="50",
            linked_metrics_config={
                "type": "sonar",
                "project_key": "my-app",
                "metric_name": "coverage"
            }
        )
        self.session.add(kr)

        # 2. 模拟 Sonar 采集到的最新数据
        s_project = SonarProject(key="my-app", name="Test App")
        self.session.add(s_project)
        self.session.flush()

        measure = SonarMeasure(
            project_id=s_project.id,
            coverage=65.0,
            analysis_date=datetime.now(timezone.utc)
        )
        self.session.add(measure)
        self.session.commit()

        # 3. 执行更新
        self.service.update_all_active_okrs()

        # 4. 验证结果
        # 进度应为: (65 - 50) / (80 - 50) = 15 / 30 = 50%
        updated_kr = self.session.query(OKRKeyResult).filter_by(title="单测覆盖率达到 80%").first()
        self.assertEqual(updated_kr.current_value, "65.0")
        self.assertEqual(updated_kr.progress, 50)

    def test_update_git_commit_count(self):
        """测试 Git 提交数自动更新。"""
        # 1. 准备目标数据
        obj = OKRObjective(title="增强产出", status="active")
        self.session.add(obj)
        self.session.flush()

        kr = OKRKeyResult(
            objective_id=obj.id,
            title="Q1 提交 100 个 Commit",
            initial_value="0",
            target_value="100",
            linked_metrics_config={
                "type": "git_commit_count",
                "project_id": 1
            }
        )
        self.session.add(kr)

        # 2. 模拟 Git 提交数据
        for i in range(75):
            c = Commit(id=f"sha_{i}", project_id=1, author_name="test", authored_date=datetime.now())
            self.session.add(c)
        
        self.session.commit()

        # 3. 执行更新
        self.service.update_all_active_okrs()

        # 4. 验证
        updated_kr = self.session.query(OKRKeyResult).filter_by(title="Q1 提交 100 个 Commit").first()
        self.assertEqual(updated_kr.current_value, "75")
        self.assertEqual(updated_kr.progress, 75)

if __name__ == '__main__':
    unittest.main()

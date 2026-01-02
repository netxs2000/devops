"""TODO: Add module description."""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, User, Organization, OKRObjective, OKRKeyResult

class TestOKRModels(unittest.TestCase):
    """OKR 模型单元测试。
    
    验证 OKR 目标及其关键结果的层级结构、关联关系以及数据完整性。
    """

    def setUp(self):
        """测试环境初始化：使用内存数据库。"""
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        """清理测试环境。"""
        self.session.close()

    def test_okr_hierarchy_and_ownership(self):
        """测试 OKR 目标的层级结构与归属关系。"""
        center = Organization(name='研发中心', level='Center')
        dept = Organization(name='架构部', level='Department')
        user = User(username='leader_a', name='张三', email='zhangsan@example.com')
        self.session.add_all([center, dept, user])
        self.session.flush()
        company_obj = OKRObjective(title='提升公司数字化转型深度', period='2025-Annual', status='active', owner_id=user.id, organization_id=center.id)
        self.session.add(company_obj)
        self.session.flush()
        dept_obj = OKRObjective(title='完成 DevOps 平台全量上线', period='2025-Q1', status='active', parent_id=company_obj.id, owner_id=user.id, organization_id=dept.id)
        self.session.add(dept_obj)
        self.session.commit()
        saved_dept_obj = self.session.query(OKRObjective).filter_by(title='完成 DevOps 平台全量上线').first()
        self.assertIsNotNone(saved_dept_obj)
        self.assertEqual(saved_dept_obj.parent.title, '提升公司数字化转型深度')
        self.assertEqual(saved_dept_obj.owner.name, '张三')
        self.assertEqual(saved_dept_obj.organization.name, '架构部')
        saved_company_obj = self.session.query(OKRObjective).filter_by(title='提升公司数字化转型深度').first()
        self.assertEqual(len(saved_company_obj.children), 1)
        self.assertEqual(saved_company_obj.children[0].title, '完成 DevOps 平台全量上线')

    def test_okr_key_results_logic(self):
        """测试 OKR 关键结果 (KR) 的关联与度量逻辑。"""
        objective = OKRObjective(title='优化系统稳定性', period='2025-Q1')
        self.session.add(objective)
        self.session.flush()
        kr1 = OKRKeyResult(objective_id=objective.id, title='核心接口耗时降至 200ms 以下', target_value='200', current_value='450', metric_unit='ms', progress=40, linked_metrics_config={'source': 'prometheus', 'query': 'avg_latency'})
        kr2 = OKRKeyResult(objective_id=objective.id, title='代码覆盖率提升至 80%', target_value='80', current_value='65', metric_unit='%', progress=60, linked_metrics_config={'source': 'sonarqube', 'metric': 'coverage'})
        self.session.add_all([kr1, kr2])
        self.session.commit()
        saved_obj = self.session.query(OKRObjective).filter_by(title='优化系统稳定性').first()
        self.assertEqual(len(saved_obj.key_results), 2)
        krs = sorted(saved_obj.key_results, key=lambda x: x.progress)
        self.assertEqual(krs[0].metric_unit, 'ms')
        self.assertEqual(krs[0].progress, 40)
        self.assertEqual(krs[1].progress, 60)
        self.assertEqual(krs[1].linked_metrics_config['source'], 'sonarqube')

    def test_cascade_delete(self):
        """测试级联删除：删除 Objective 时应同步删除 KRs。"""
        objective = OKRObjective(title='临时目标', period='Test')
        self.session.add(objective)
        self.session.flush()
        kr = OKRKeyResult(objective_id=objective.id, title='临时 KR')
        self.session.add(kr)
        self.session.commit()
        self.session.delete(objective)
        self.session.commit()
        remaining_krs = self.session.query(OKRKeyResult).filter_by(title='临时 KR').count()
        self.assertEqual(remaining_krs, 0)

    def test_okr_product_binding(self):
        """测试 OKR 与 Product 的绑定关系。"""
        from devops_collector.models.base_models import Product
        product = Product(name='智慧金融分析系统', level='Product')
        self.session.add(product)
        self.session.flush()
        objective = OKRObjective(title='Q1 产品稳定性提升', period='2025-Q1', product_id=product.id)
        self.session.add(objective)
        self.session.commit()
        saved_prod = self.session.query(Product).filter_by(name='智慧金融分析系统').first()
        self.assertEqual(len(saved_prod.objectives), 1)
        self.assertEqual(saved_prod.objectives[0].title, 'Q1 产品稳定性提升')
        saved_obj = self.session.query(OKRObjective).filter_by(title='Q1 产品稳定性提升').first()
        self.assertEqual(saved_obj.product.name, '智慧金融分析系统')
if __name__ == '__main__':
    unittest.main()
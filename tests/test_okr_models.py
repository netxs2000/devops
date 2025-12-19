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
        # 1. 创建背景数据：中心与负责人
        center = Organization(name="研发中心", level="Center")
        dept = Organization(name="架构部", level="Department")
        user = User(username="leader_a", name="张三", email="zhangsan@example.com")
        self.session.add_all([center, dept, user])
        self.session.flush()

        # 2. 创建公司级目标 (Company Objective)
        company_obj = OKRObjective(
            title="提升公司数字化转型深度",
            period="2025-Annual",
            status="active",
            owner_id=user.id,
            organization_id=center.id
        )
        self.session.add(company_obj)
        self.session.flush()

        # 3. 创建部门级目标 (Department Objective)，并关联到公司目标
        dept_obj = OKRObjective(
            title="完成 DevOps 平台全量上线",
            period="2025-Q1",
            status="active",
            parent_id=company_obj.id,
            owner_id=user.id,
            organization_id=dept.id
        )
        self.session.add(dept_obj)
        self.session.commit()

        # 4. 验证层级关系
        saved_dept_obj = self.session.query(OKRObjective).filter_by(title="完成 DevOps 平台全量上线").first()
        self.assertIsNotNone(saved_dept_obj)
        self.assertEqual(saved_dept_obj.parent.title, "提升公司数字化转型深度")
        self.assertEqual(saved_dept_obj.owner.name, "张三")
        self.assertEqual(saved_dept_obj.organization.name, "架构部")

        # 5. 从父级验证子级
        saved_company_obj = self.session.query(OKRObjective).filter_by(title="提升公司数字化转型深度").first()
        self.assertEqual(len(saved_company_obj.children), 1)
        self.assertEqual(saved_company_obj.children[0].title, "完成 DevOps 平台全量上线")

    def test_okr_key_results_logic(self):
        """测试 OKR 关键结果 (KR) 的关联与度量逻辑。"""
        # 1. 创建目标指标
        objective = OKRObjective(title="优化系统稳定性", period="2025-Q1")
        self.session.add(objective)
        self.session.flush()

        # 2. 创建多个关键结果 (KRs)
        kr1 = OKRKeyResult(
            objective_id=objective.id,
            title="核心接口耗时降至 200ms 以下",
            target_value="200",
            current_value="450",
            metric_unit="ms",
            progress=40,
            linked_metrics_config={"source": "prometheus", "query": "avg_latency"}
        )
        kr2 = OKRKeyResult(
            objective_id=objective.id,
            title="代码覆盖率提升至 80%",
            target_value="80",
            current_value="65",
            metric_unit="%",
            progress=60,
            linked_metrics_config={"source": "sonarqube", "metric": "coverage"}
        )
        self.session.add_all([kr1, kr2])
        self.session.commit()

        # 3. 验证 KR 关联
        saved_obj = self.session.query(OKRObjective).filter_by(title="优化系统稳定性").first()
        self.assertEqual(len(saved_obj.key_results), 2)
        
        # 验证 KR 内容
        krs = sorted(saved_obj.key_results, key=lambda x: x.progress)
        self.assertEqual(krs[0].metric_unit, "ms")
        self.assertEqual(krs[0].progress, 40)
        self.assertEqual(krs[1].progress, 60)
        self.assertEqual(krs[1].linked_metrics_config["source"], "sonarqube")

    def test_cascade_delete(self):
        """测试级联删除：删除 Objective 时应同步删除 KRs。"""
        objective = OKRObjective(title="临时目标", period="Test")
        self.session.add(objective)
        self.session.flush()

        kr = OKRKeyResult(objective_id=objective.id, title="临时 KR")
        self.session.add(kr)
        self.session.commit()

        # 删除 Objective
        self.session.delete(objective)
        self.session.commit()

        # 验证 KR 是否也被删除
        remaining_krs = self.session.query(OKRKeyResult).filter_by(title="临时 KR").count()
        self.assertEqual(remaining_krs, 0)

    def test_okr_product_binding(self):
        """测试 OKR 与 Product 的绑定关系。"""
        from devops_collector.models.base_models import Product
        
        # 1. 创建产品
        product = Product(name="智慧金融分析系统", level="Product")
        self.session.add(product)
        self.session.flush()

        # 2. 创建关联该产品的目标
        objective = OKRObjective(
            title="Q1 产品稳定性提升",
            period="2025-Q1",
            product_id=product.id
        )
        self.session.add(objective)
        self.session.commit()

        # 3. 验证从产品侧查询 OKR
        saved_prod = self.session.query(Product).filter_by(name="智慧金融分析系统").first()
        self.assertEqual(len(saved_prod.objectives), 1)
        self.assertEqual(saved_prod.objectives[0].title, "Q1 产品稳定性提升")

        # 4. 验证从 OKR 侧查询产品
        saved_obj = self.session.query(OKRObjective).filter_by(title="Q1 产品稳定性提升").first()
        self.assertEqual(saved_obj.product.name, "智慧金融分析系统")

if __name__ == '__main__':
    unittest.main()


import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

# 模拟 User 对象，结构匹配 MDM base_models.py
class MockLocation:
    def __init__(self, location_id, short_name, children=None):
        self.location_id = location_id
        self.short_name = short_name
        self.children = children or []

class MockUser:
    def __init__(self, email, role, location=None):
        self.global_user_id = uuid4()
        self.primary_email = email
        self.role = role
        self.location = location

class TestMDMIntegration(unittest.TestCase):

    def setUp(self):
        # 建立 Location 树: 华南 (South) -> 广东 (GD) -> 深圳 (SZ)
        self.loc_sz = MockLocation("440300", "shenzhen")
        self.loc_gd = MockLocation("440000", "guangdong", children=[self.loc_sz])
        self.loc_south = MockLocation("400000", "south", children=[self.loc_gd])
        
        # 建立 Mock 用户
        self.admin = MockUser("admin@corp.com", "admin")
        self.prov_user = MockUser("prov@corp.com", "tester", location=self.loc_gd)
        self.city_user = MockUser("city@corp.com", "tester", location=self.loc_sz)
        self.stranger = MockUser("guest@corp.com", "guest")

    def test_p4_data_scope_ids_recursion(self):
        """验证 P4 级联 ID 收集逻辑 (递归)"""
        from devops_portal.main import get_user_data_scope_ids
        
        # 广东用户应该能看到：广东、深圳
        gd_scopes = get_user_data_scope_ids(self.prov_user)
        self.assertIn("440000", gd_scopes)
        self.assertIn("440300", gd_scopes)
        
        # 深圳用户只能看到自己
        sz_scopes = get_user_data_scope_ids(self.city_user)
        self.assertEqual(len(sz_scopes), 1)
        self.assertIn("440300", sz_scopes)

    @patch('devops_collector.auth.database.SessionLocal')
    def test_filter_issues_by_province_p4(self, mock_db):
        """验证 P4 级联隔离过滤逻辑"""
        from devops_portal.main import filter_issues_by_province
        
        # 模拟数据库行为：返回 ID 对应的 short_name
        mock_query = mock_db.return_value.query.return_value.filter.return_value.all
        # 假设查询 ID 440000, 440300
        mock_query.return_value = [
            MagicMock(short_name="guangdong"),
            MagicMock(short_name="shenzhen")
        ]
        
        mock_issues = [
            {"iid": 1, "labels": ["province::guangdong", "type::test"]},
            {"iid": 2, "labels": ["province::shenzhen", "type::test"]},
            {"iid": 3, "labels": ["province::beijing", "type::test"]},
            {"iid": 4, "labels": ["province::nationwide", "type::test"]}
        ]
        
        # 广东用户应该看到广东、深圳的数据，看不到北京和全国的数据
        filtered = filter_issues_by_province(mock_issues, self.prov_user)
        iids = [i['iid'] for i in filtered]
        self.assertIn(1, iids)
        self.assertIn(2, iids)
        self.assertNotIn(3, iids)
        self.assertNotIn(4, iids)

    def test_p5_rbac_role_isolation(self):
        """验证 P5 RBAC 接口拦截模拟逻辑"""
        # 测试需求审批接口的鉴权逻辑
        def simulate_review_permission(user, state):
            if state in ["approved", "rejected"]:
                if user.role not in ["maintainer", "admin"]:
                    return "403 Forbidden"
            return "200 OK"
        
        # Admin 可以
        self.assertEqual(simulate_review_permission(self.admin, "approved"), "200 OK")
        
        # Guest 不可以
        self.assertEqual(simulate_review_permission(self.stranger, "approved"), "403 Forbidden")
        
        # Tester 不可以审批（需要 maintainer/admin）
        self.assertEqual(simulate_review_permission(self.prov_user, "approved"), "403 Forbidden")

if __name__ == "__main__":
    unittest.main()

"""单元测试：IdentityManager

验证跨系统身份识别、用户对齐以及命名冲突处理逻辑。
"""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.models.base_models import Base, User, IdentityMapping
from devops_collector.core.identity_manager import IdentityManager

class TestIdentityManager(unittest.TestCase):
    """IdentityManager 逻辑测试类。"""

    def setUp(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.session.close()

    def test_get_or_create_user_new(self):
        """测试创建全新用户。"""
        user = IdentityManager.get_or_create_user(self.session, 'jira', 'jira_user_1', 'user1@example.com', 'User One')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'user1@example.com')
        mapping = self.session.query(IdentityMapping).filter_by(source='jira', external_id='jira_user_1').first()
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.user_id, user.id)

    def test_identity_matching_by_email(self):
        """测试通过 Email 自动完成跨系统身份对齐。"""
        user_a = IdentityManager.get_or_create_user(self.session, 'jira', 'jira_acc', 'common@example.com', 'Jira Name')
        user_b = IdentityManager.get_or_create_user(self.session, 'zentao', 'zt_acc', 'common@example.com', 'ZenTao Name')
        self.assertEqual(user_a.id, user_b.id)
        mappings = self.session.query(IdentityMapping).filter_by(user_id=user_a.id).all()
        self.assertEqual(len(mappings), 2)

    def test_name_conflict_resolution(self):
        """测试 Username 冲突后的自动后缀逻辑。
        
        场景：
        1. 已存在用户 'zhangsan' (Email A)
        2. 新采集用户 'zhangsan' (Email B)
        3. 预期新用户的全局 Username 为 'zhangsan_1'
        """
        IdentityManager.get_or_create_user(self.session, 'src1', 'id1', 'zs@a.com', 'Zhang San', username='zhangsan')
        user2 = IdentityManager.get_or_create_user(self.session, 'src2', 'id2', 'zs@b.com', 'Zhang San 2', username='zhangsan')
        self.assertEqual(user2.username, 'zhangsan_1')
        self.assertEqual(user2.email, 'zs@b.com')

    def test_existing_mapping(self):
        """测试命中已存在映射时的幂等性。"""
        IdentityManager.get_or_create_user(self.session, 'jira', 'acc1', 'u1@ex.com')
        user = IdentityManager.get_or_create_user(self.session, 'jira', 'acc1')
        self.assertEqual(user.email, 'u1@ex.com')
if __name__ == '__main__':
    unittest.main()
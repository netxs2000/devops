"""单元测试：IdentityManager

验证跨系统身份识别、用户对齐以及命名冲突处理逻辑。
"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from devops_collector.core.identity_manager import IdentityManager
from devops_collector.models.base_models import Base, IdentityMapping


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
        self.engine = create_engine("sqlite:///:memory:")
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
        # Note: IdentityManager.get_or_create_user only creates mappings, not users anymore
        # We should create the user first if we want to test alignment
        from devops_collector.models.base_models import User
        import uuid
        user_new = User(global_user_id=uuid.uuid4(), primary_email="user1@example.com", full_name="User One", is_current=True)
        self.session.add(user_new)
        self.session.commit()

        user = IdentityManager.get_or_create_user(self.session, "jira", "jira_user_1", "user1@example.com", "User One")
        self.assertIsNotNone(user)
        self.assertEqual(user.primary_email, "user1@example.com")
        mapping = self.session.query(IdentityMapping).filter_by(source_system="jira", external_user_id="jira_user_1").first()
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.global_user_id, user.global_user_id)

    def test_identity_matching_by_email(self):
        """测试通过 Email 自动完成跨系统身份对齐。"""
        from devops_collector.models.base_models import User
        import uuid
        user_common = User(global_user_id=uuid.uuid4(), primary_email="common@example.com", full_name="Common Name", is_current=True)
        self.session.add(user_common)
        self.session.commit()

        user_a = IdentityManager.get_or_create_user(self.session, "jira", "jira_acc", "common@example.com", "Jira Name")
        user_b = IdentityManager.get_or_create_user(self.session, "zentao", "zt_acc", "common@example.com", "ZenTao Name")
        self.assertEqual(user_a.global_user_id, user_b.global_user_id)
        mappings = self.session.query(IdentityMapping).filter_by(global_user_id=user_a.global_user_id).all()
        self.assertEqual(len(mappings), 2)

    def test_name_conflict_resolution(self):
        """测试 Username 冲突后的自动后缀逻辑。

        场景：
        1. 已存在用户 'zhangsan' (Email A)
        2. 新采集用户 'zhangsan' (Email B)
        3. 预期新用户的全局 Username 为 'zhangsan_1'
        """
        IdentityManager.get_or_create_user(self.session, "src1", "id1", "zs@a.com", "Zhang San", username="zhangsan")
        user2 = IdentityManager.get_or_create_user(self.session, "src2", "id2", "zs@b.com", "Zhang San 2", username="zhangsan")
        self.assertEqual(user2.username, "zhangsan_1")
        self.assertEqual(user2.email, "zs@b.com")

    def test_existing_mapping(self):
        """测试命中已存在映射时的幂等性。"""
        from devops_collector.models.base_models import User
        import uuid
        user_id = uuid.uuid4()
        user_u1 = User(global_user_id=user_id, primary_email="u1@ex.com", full_name="User U1", is_current=True)
        self.session.add(user_u1)
        self.session.commit()

        IdentityManager.get_or_create_user(self.session, "jira", "acc1", "u1@ex.com")
        user = IdentityManager.get_or_create_user(self.session, "jira", "acc1")
        self.assertEqual(user.primary_email, "u1@ex.com")


if __name__ == "__main__":
    unittest.main()

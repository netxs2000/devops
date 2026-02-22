"""Nexus Worker 单元测试"""
import unittest
from unittest.mock import MagicMock, patch

from devops_collector.plugins.nexus.models import NexusComponent
from devops_collector.plugins.nexus.worker import NexusWorker


class TestNexusWorker(unittest.TestCase):
    def setUp(self):
        self.session = MagicMock()
        self.client = MagicMock()
        self.worker = NexusWorker(self.session, self.client)

        # 模拟产品数据 (带 matching_patterns 字段)
        self.mock_products = [
            MagicMock(product_id="devops", matching_patterns=None, is_current=True),
            MagicMock(product_id="portal", matching_patterns=None, is_current=True),
            MagicMock(product_id="collector", matching_patterns=None, is_current=True)
        ]
        # 统一设置 query().filter().all() 的返回值
        self.session.query.return_value.filter.return_value.all.return_value = self.mock_products

    def test_product_cache_init(self):
        """测试产品缓存初始化。"""
        self.worker._init_product_cache()
        self.assertIn('devops', self.worker._product_map)
        self.assertEqual(self.worker._product_map['devops'], 'devops')

    def test_resolve_product_id_by_group(self):
        """测试通过 Group 自动识别产品。"""
        self.worker._init_product_cache()

        # 匹配 devops
        pid = self.worker._resolve_product_id("com.tjhq.devops", "some-lib")
        self.assertEqual(pid, "devops")

        # 匹配 portal
        pid = self.worker._resolve_product_id("org.company.portal.submodule", "api")
        self.assertEqual(pid, "portal")

    def test_resolve_product_id_by_name(self):
        """测试通过组件名称精确匹配产品。"""
        self.worker._init_product_cache()

        pid = self.worker._resolve_product_id("random.group", "collector")
        self.assertEqual(pid, "collector")

    def test_resolve_product_id_by_explicit_patterns(self):
        """测试通过显式定义的 matching_patterns 进行正则匹配。"""
        # 模拟带正则的产品
        mock_products = [
            MagicMock(product_id="security-app", matching_patterns=["^sec-.*", "com.tjhq.security.*"], is_current=True),
        ]
        self.session.query.return_value.filter.return_value.all.return_value = mock_products
        self.worker._init_product_cache()

        # 1. 匹配名称前缀
        self.assertEqual(self.worker._resolve_product_id(None, "sec-scanner"), "security-app")
        # 2. 匹配 Group 前缀
        self.assertEqual(self.worker._resolve_product_id("com.tjhq.security.api", "util"), "security-app")
        # 3. 不匹配
        self.assertIsNone(self.worker._resolve_product_id("com.other", "app"))

    def test_resolve_product_id_not_found(self):
        """测试匹配失败情况。"""
        self.worker._init_product_cache()

        pid = self.worker._resolve_product_id("unknown.group", "unknown-lib")
        self.assertIsNone(pid)

    @patch('devops_collector.core.base_worker.BaseWorker.save_to_staging')
    def test_save_batch_with_auto_mapping(self, mock_staging):
        """测试批量保存时的自动映射逻辑。"""
        self.worker._init_product_cache()
        self.session.query(NexusComponent).filter_by().first.return_value = None

        batch = [{
            'id': 'comp1',
            'repository': 'maven-public',
            'format': 'maven2',
            'group': 'com.tjhq.devops',
            'name': 'core',
            'version': '1.0.0'
        }]

        self.worker._save_batch(batch)

        # 验证是否创建了组件且绑定了 product_id
        args, kwargs = self.session.add.call_args
        comp = args[0]
        self.assertIsInstance(comp, NexusComponent)
        self.assertEqual(comp.product_id, "devops")
        self.session.commit.assert_called_once()

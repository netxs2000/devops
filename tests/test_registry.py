"""单元测试：PluginRegistry

验证插件的注册、查询和实例化功能。
"""
import unittest
from devops_collector.core.registry import PluginRegistry

class MockClient:
    """Mock 客户端类。"""

    def __init__(self, **kwargs):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.kwargs = kwargs

class MockWorker:
    """Mock Worker 类。"""

    def __init__(self, session, client, **kwargs):
        '''"""TODO: Add description.

Args:
    self: TODO
    session: TODO
    client: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.session = session
        self.client = client
        self.kwargs = kwargs

class TestPluginRegistry(unittest.TestCase):
    """PluginRegistry 功能测试类。"""

    def setUp(self):
        """每个测试前清空注册表。"""
        PluginRegistry.clear()

    def test_register_and_get(self):
        """测试基础的注册与获取逻辑。"""
        PluginRegistry.register_client('test_src', MockClient)
        client_cls = PluginRegistry.get_client('test_src')
        self.assertEqual(client_cls, MockClient)
        self.assertIsNone(PluginRegistry.get_client('non_existent'))

    def test_factory_methods(self):
        """测试实例化工厂方法。"""
        PluginRegistry.register_client('test_src', MockClient)
        PluginRegistry.register_worker('test_src', MockWorker)
        client_inst = PluginRegistry.get_client_instance('test_src', url='http://mock')
        self.assertIsInstance(client_inst, MockClient)
        self.assertEqual(client_inst.kwargs['url'], 'http://mock')
        mock_session = 'session_obj'
        worker_inst = PluginRegistry.get_worker_instance('test_src', mock_session, client_inst, mode='sync')
        self.assertIsInstance(worker_inst, MockWorker)
        self.assertEqual(worker_inst.session, mock_session)
        self.assertEqual(worker_inst.client, client_inst)
        self.assertEqual(worker_inst.kwargs['mode'], 'sync')

    def test_list_plugins(self):
        """测试列表查询功能。"""
        PluginRegistry.register_client('gitlab', MockClient)
        PluginRegistry.register_worker('zentao', MockWorker)
        plugins = PluginRegistry.list_plugins()
        self.assertIn('gitlab', plugins)
        self.assertIn('zentao', plugins)
        self.assertEqual(plugins['gitlab']['client'], 'MockClient')
if __name__ == '__main__':
    unittest.main()
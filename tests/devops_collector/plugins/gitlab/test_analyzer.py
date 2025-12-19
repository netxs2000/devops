
import unittest
from devops_collector.plugins.gitlab.analyzer import DiffAnalyzer

class TestDiffAnalyzer(unittest.TestCase):
    """测试代码差异分析器与文件分类逻辑。"""

    def test_get_file_category_code(self):
        """测试普通的工程代码分类。"""
        self.assertEqual(DiffAnalyzer.get_file_category('src/main.py'), 'Code')
        self.assertEqual(DiffAnalyzer.get_file_category('lib/utils.java'), 'Code')
        self.assertEqual(DiffAnalyzer.get_file_category('app/controllers/user_controller.rb'), 'Code')

    def test_get_file_category_test(self):
        """测试测试代码分类。"""
        self.assertEqual(DiffAnalyzer.get_file_category('tests/test_main.py'), 'Test')
        self.assertEqual(DiffAnalyzer.get_file_category('src/main_test.go'), 'Test')
        self.assertEqual(DiffAnalyzer.get_file_category('test/unit/utils_spec.js'), 'Test')

    def test_get_file_category_iac(self):
        """测试基础设施代码分类。"""
        self.assertEqual(DiffAnalyzer.get_file_category('Dockerfile'), 'IaC')
        self.assertEqual(DiffAnalyzer.get_file_category('deploy/k8s/deployment.yaml'), 'IaC')
        self.assertEqual(DiffAnalyzer.get_file_category('terraform/main.tf'), 'IaC')
        self.assertEqual(DiffAnalyzer.get_file_category('.gitlab-ci.yml'), 'IaC')
        self.assertEqual(DiffAnalyzer.get_file_category('scripts/deploy.sh'), 'IaC')

    def test_get_file_category_config(self):
        """测试配置文件分类。"""
        self.assertEqual(DiffAnalyzer.get_file_category('config/settings.yaml'), 'Config')
        self.assertEqual(DiffAnalyzer.get_file_category('src/main/resources/application.properties'), 'Config')
        self.assertEqual(DiffAnalyzer.get_file_category('etc/nginx.conf'), 'Config')
        self.assertEqual(DiffAnalyzer.get_file_category('app.ini'), 'Config')

    def test_analyze_diff_basic(self):
        """测试基础的代码行统计。"""
        diff_text = """@@ -1,3 +1,4 @@
-old code
+new code
+# comment line
+
+"""
        stats = DiffAnalyzer.analyze_diff(diff_text, 'test.py')
        self.assertEqual(stats['code_deleted'], 1)
        self.assertEqual(stats['code_added'], 1)
        self.assertEqual(stats['comment_added'], 1)
        self.assertEqual(stats['blank_added'], 1)

    def test_is_ignored(self):
        """测试文件过滤。"""
        self.assertTrue(DiffAnalyzer.is_ignored('package-lock.json'))
        self.assertTrue(DiffAnalyzer.is_ignored('node_modules/vue/index.js'))
        self.assertFalse(DiffAnalyzer.is_ignored('src/index.js'))

if __name__ == '__main__':
    unittest.main()

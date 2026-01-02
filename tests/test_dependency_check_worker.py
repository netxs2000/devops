"""
OWASP Dependency-Check Worker 单元测试
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path
from devops_collector.plugins.dependency_check.worker import DependencyCheckWorker
from devops_collector.plugins.dependency_check.client import DependencyCheckClient

class TestDependencyCheckClient(unittest.TestCase):
    """测试 DependencyCheckClient"""

    def setUp(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.client = DependencyCheckClient(cli_path='/usr/bin/dependency-check', timeout=300)

    @patch('subprocess.run')
    def test_scan_project_success(self, mock_run):
        """测试成功扫描项目"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        with patch('pathlib.Path.exists', return_value=True):
            report_path = self.client.scan_project(project_path='/path/to/project', output_dir='/tmp/reports')
            self.assertIsNotNone(report_path)
            self.assertIn('dependency-check-report.json', report_path)

    @patch('subprocess.run')
    def test_scan_project_timeout(self, mock_run):
        """测试扫描超时"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 300)
        with self.assertRaises(RuntimeError):
            self.client.scan_project(project_path='/path/to/project', output_dir='/tmp/reports')

    def test_parse_report(self):
        """测试解析报告"""
        test_report = {'dependencies': [{'fileName': 'test-1.0.0.jar', 'license': 'Apache-2.0', 'vulnerabilities': []}]}
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(test_report))):
            result = self.client.parse_report('/tmp/test-report.json')
            self.assertEqual(len(result['dependencies']), 1)

class TestDependencyCheckWorker(unittest.TestCase):
    """测试 DependencyCheckWorker"""

    def setUp(self):
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        self.config = {'dependency_check': {'cli_path': '/usr/bin/dependency-check', 'timeout': 300}}
        self.worker = DependencyCheckWorker(self.config)

    def test_normalize_license_spdx(self):
        """测试许可证 SPDX 规范化"""
        test_cases = [('Apache License 2.0', 'Apache-2.0'), ('MIT License', 'MIT'), ('GPL-3.0', 'GPL-3.0'), ('Unknown License', 'UNKNOWN')]
        for license_str, expected_spdx in test_cases:
            result = self.worker._normalize_license_spdx(license_str)
            self.assertEqual(result, expected_spdx, f'Failed for {license_str}')

    def test_detect_package_manager(self):
        """测试包管理器检测"""
        test_cases = [({'filePath': '/path/to/pom.xml'}, 'maven'), ({'filePath': '/path/to/package.json'}, 'npm'), ({'filePath': '/path/to/requirements.txt'}, 'pypi'), ({'filePath': '/path/to/project.csproj'}, 'nuget'), ({'filePath': '/path/to/go.mod'}, 'go')]
        for dep_data, expected_pm in test_cases:
            result = self.worker._detect_package_manager(dep_data)
            self.assertEqual(result, expected_pm)

    def test_analyze_vulnerabilities(self):
        """测试漏洞分析"""
        vulnerabilities = [{'name': 'CVE-2023-12345', 'severity': 'CRITICAL', 'cvssv3': {'baseScore': 9.8}}, {'name': 'CVE-2023-67890', 'severity': 'HIGH', 'cvssv3': {'baseScore': 7.5}}, {'name': 'CVE-2023-11111', 'severity': 'MEDIUM', 'cvssv3': {'baseScore': 5.0}}]
        stats = self.worker._analyze_vulnerabilities(vulnerabilities)
        self.assertEqual(stats['critical'], 1)
        self.assertEqual(stats['high'], 1)
        self.assertEqual(stats['medium'], 1)
        self.assertEqual(stats['highest_cvss'], 9.8)

    def test_assess_license_risk(self):
        """测试许可证风险评估"""
        test_cases = [('GPL-3.0', 'critical'), ('AGPL-3.0', 'critical'), ('LGPL-3.0', 'high'), ('Apache-2.0', 'low'), ('MIT', 'low'), ('UNKNOWN', 'unknown')]
        for spdx_id, expected_risk in test_cases:
            result = self.worker._assess_license_risk(spdx_id)
            self.assertEqual(result, expected_risk, f'Failed for {spdx_id}')

    def test_extract_cvss_score(self):
        """测试 CVSS 评分提取"""
        vuln_v3 = {'cvssv3': {'baseScore': 7.5}}
        self.assertEqual(self.worker._extract_cvss_score(vuln_v3), 7.5)
        vuln_v2 = {'cvssv2': {'score': 6.0}}
        self.assertEqual(self.worker._extract_cvss_score(vuln_v2), 6.0)
        vuln_none = {}
        self.assertIsNone(self.worker._extract_cvss_score(vuln_none))
if __name__ == '__main__':
    unittest.main()
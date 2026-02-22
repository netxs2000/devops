"""
OWASP Dependency-Check Worker 单元测试
"""
import unittest
from unittest.mock import MagicMock

from devops_collector.plugins.dependency_check.worker import DependencyCheckWorker


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
        self.worker = DependencyCheckWorker(MagicMock(), MagicMock())
        self.worker.session = MagicMock()

    def test_process_task_routing(self):
        """测试任务路由逻辑"""
        # Case 1: CI Report Mode
        with indent_mock_process_ci_report(self.worker) as mock_ci:
            self.worker.process_task({'project_id': 1, 'report_json': {}})
            mock_ci.assert_called_once()

        # Case 2: Invalid Input
        with self.assertRaises(ValueError):
            self.worker.process_task({'project_id': 1})

    def test_process_ci_report_success(self):
        """测试成功处理 CI 报告"""
        # Mock Session and Data
        mock_scan = MagicMock()
        mock_scan.id = 100
        self.worker.session.add = MagicMock()
        self.worker.session.commit = MagicMock()
        # Mock add() to set ID
        def set_id(obj):
            obj.id = 100
        self.worker.session.add.side_effect = set_id

        # Mock _save_dependencies
        self.worker._save_dependencies = MagicMock(return_value={
            'total': 10, 'vulnerable': 2, 'high_risk_licenses': 1
        })

        task = {
            'project_id': 1,
            'report_json': {'reportSchema': '1.0', 'dependencies': []},
            'ci_job_id': 'job-123',
            'commit_sha': 'abcdef',
            'branch': 'main'
        }

        scan_id = self.worker.process_ci_report(1, task)

        self.assertEqual(scan_id, 100)
        self.worker.session.add.assert_called_once()
        self.worker._save_dependencies.assert_called_once()
        self.assertEqual(self.worker.session.commit.call_count, 2) # add + update

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

# Helper context managers for patching methods on the instance
from contextlib import contextmanager


@contextmanager
def indent_mock_process_ci_report(worker):
    original = worker.process_ci_report
    worker.process_ci_report = MagicMock()
    yield worker.process_ci_report
    worker.process_ci_report = original

if __name__ == '__main__':
    unittest.main()

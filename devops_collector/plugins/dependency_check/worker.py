"""
OWASP Dependency-Check Worker
采集项目的依赖清单、许可证信息和漏洞信息
"""
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from devops_collector.core.base_worker import BaseWorker
from devops_collector.core.registry import PluginRegistry
from devops_collector.models.dependency import (
    Dependency,
    DependencyCVE,
    DependencyScan,
    LicenseRiskRule,
)


logger = logging.getLogger(__name__)

class DependencyCheckWorker(BaseWorker):
    """OWASP Dependency-Check 数据采集器"""
    SCHEMA_VERSION = '1.0.0'
    LICENSE_SPDX_MAPPING = {'Apache License 2.0': 'Apache-2.0', 'Apache License, Version 2.0': 'Apache-2.0', 'Apache 2.0': 'Apache-2.0', 'MIT License': 'MIT', 'The MIT License': 'MIT', 'BSD 3-Clause': 'BSD-3-Clause', 'BSD 2-Clause': 'BSD-2-Clause', 'GPL-3.0': 'GPL-3.0', 'GPL-2.0': 'GPL-2.0', 'LGPL-3.0': 'LGPL-3.0', 'LGPL-2.1': 'LGPL-2.1', 'AGPL-3.0': 'AGPL-3.0', 'MPL-2.0': 'MPL-2.0', 'EPL-2.0': 'EPL-2.0'}

    def __init__(self, session: Session, client: Any = None, report_dir: str = '/var/lib/devops/dependency-reports', keep_reports: bool = True, retention_days: int = 90):
        """初始化"""
        super().__init__(session, client)
        self.report_base_dir = report_dir
        self.keep_reports = keep_reports
        self.report_retention_days = retention_days
        Path(self.report_base_dir).mkdir(parents=True, exist_ok=True)
        self.license_rules = self._load_license_rules()
        self.scanner_version = self.client.get_version() if self.client else 'unknown'

    def _load_license_rules(self) -> dict[str, LicenseRiskRule]:
        """加载许可证风险规则"""
        rules = {}
        try:
            for rule in self.session.query(LicenseRiskRule).filter_by(is_active=True).all():
                if rule.license_spdx_id:
                    rules[rule.license_spdx_id] = rule
                rules[rule.license_name] = rule
            logger.info(f'Loaded {len(rules)} license risk rules')
        except Exception as e:
            logger.error(f'Failed to load license rules: {e}')
        return rules

    def process_task(self, task: dict) -> Any:
        """
        处理依赖扫描任务
        
        仅支持 CI 报告导入模式: task 中必须包含 'report_json' 或 'report_path'
        """
        project_id = task.get('project_id')
        if not project_id:
            raise ValueError("Task missing 'project_id'")

        if 'report_json' not in task and 'report_path' not in task:
            raise ValueError("Task must contain 'report_json' or 'report_path'")

        return self.process_ci_report(project_id, task)

    def process_ci_report(self, project_id: int, task: dict) -> int:
        """
        处理 CI 流水线上传的报告
        """
        import json

        # 1. 获取报告内容
        report_data = task.get('report_json')
        report_path = task.get('report_path')

        if report_data is None and report_path:
            logger.info(f"Loading report from file: {report_path}")
            if not Path(report_path).exists():
                raise FileNotFoundError(f"Report not found: {report_path}")
            with open(report_path, encoding='utf-8') as f:
                report_data = json.load(f)

        if not report_data:
            raise ValueError("No report data provided")

        # 2. 创建扫描记录
        scan = DependencyScan(
            project_id=project_id,
            scan_status='in_progress',
            scanner_name='OWASP Dependency-Check (CI)',
            scanner_version=report_data.get('reportSchema', 'unknown'),
            ci_job_id=task.get('ci_job_id'),
            ci_job_url=task.get('ci_job_url'),
            commit_sha=task.get('commit_sha'),
            branch=task.get('branch'),
            report_url=task.get('report_url'),
            scan_duration_seconds=task.get('duration'),
            raw_json=report_data if task.get('save_raw', True) else None
        )
        self.session.add(scan)
        self.session.commit()

        try:
            # 3. 解析并保存依赖
            stats = self._save_dependencies(scan.id, project_id, report_data)

            # 4. 更新记录状态
            scan.scan_status = 'completed'
            scan.total_dependencies = stats['total']
            scan.vulnerable_dependencies = stats['vulnerable']
            scan.high_risk_licenses = stats['high_risk_licenses']
            self.session.commit()

            logger.info(f"CI Report processed for project {project_id}, scan_id: {scan.id}")
            return scan.id

        except Exception as e:
            logger.error(f"Failed to process CI report: {e}")
            scan.scan_status = 'failed'
            self.session.commit()
            raise
    def cleanup_old_reports(self, dry_run: bool=False) -> dict[str, int]:
        """
        清理过期的报告文件
        """
        import shutil
        from datetime import timedelta
        if self.report_retention_days == 0:
            logger.info('Report retention is set to 0 (永久保留), skipping cleanup')
            return {'deleted_count': 0, 'freed_space_mb': 0.0}
        cutoff_date = datetime.now() - timedelta(days=self.report_retention_days)
        logger.info(f'Cleaning up reports older than {cutoff_date}')
        deleted_count = 0
        freed_space = 0
        report_base_path = Path(self.report_base_dir)
        if not report_base_path.exists():
            logger.warning(f'Report directory does not exist: {self.report_base_dir}')
            return {'deleted_count': 0, 'freed_space_mb': 0.0}
        for project_dir in report_base_path.iterdir():
            if not project_dir.is_dir():
                continue
            for scan_dir in project_dir.iterdir():
                if not scan_dir.is_dir():
                    continue
                mtime = datetime.fromtimestamp(scan_dir.stat().st_mtime)
                if mtime < cutoff_date:
                    dir_size = sum(f.stat().st_size for f in scan_dir.rglob('*') if f.is_file())
                    freed_space += dir_size
                    if dry_run:
                        logger.info(f'[DRY RUN] Would delete: {scan_dir} ({dir_size / 1024 / 1024:.2f} MB)')
                    else:
                        shutil.rmtree(scan_dir)
                        logger.info(f'Deleted old report: {scan_dir} ({dir_size / 1024 / 1024:.2f} MB)')
                    deleted_count += 1
        freed_space_mb = freed_space / 1024 / 1024
        logger.info(f'Cleanup completed: {deleted_count} directories, {freed_space_mb:.2f} MB freed')
        return {'deleted_count': deleted_count, 'freed_space_mb': round(freed_space_mb, 2)}

    def _save_dependencies(self, scan_id: int, project_id: int, report_data: dict) -> dict:
        """保存依赖清单"""
        dependencies_data = report_data.get('dependencies', [])
        stats = {'total': 0, 'vulnerable': 0, 'high_risk_licenses': 0}

        for dep_data in dependencies_data:
            package_name = dep_data.get('fileName', 'Unknown')
            package_version = self._extract_version(dep_data)
            license_info = self._extract_license(dep_data)
            license_risk = self._assess_license_risk(license_info.get('spdx_id'))
            vulnerabilities = dep_data.get('vulnerabilities', [])
            cve_stats = self._analyze_vulnerabilities(vulnerabilities)
            dependency = Dependency(scan_id=scan_id, project_id=project_id, package_name=package_name, package_version=package_version, package_manager=self._detect_package_manager(dep_data), license_name=license_info.get('name'), license_spdx_id=license_info.get('spdx_id'), license_url=license_info.get('url'), license_risk_level=license_risk, has_vulnerabilities=len(vulnerabilities) > 0, highest_cvss_score=cve_stats['highest_cvss'], critical_cve_count=cve_stats['critical'], high_cve_count=cve_stats['high'], medium_cve_count=cve_stats['medium'], low_cve_count=cve_stats['low'], file_path=dep_data.get('filePath'), description=dep_data.get('description'), raw_data=dep_data)
            self.session.add(dependency)
            self.session.flush()
            for vuln in vulnerabilities:
                cve = DependencyCVE(dependency_id=dependency.id, cve_id=vuln.get('name', 'UNKNOWN'), cvss_score=self._extract_cvss_score(vuln), cvss_vector=self._extract_cvss_vector(vuln), severity=vuln.get('severity', 'UNKNOWN'), description=vuln.get('description'), references=vuln.get('references', []))
                self.session.add(cve)
            stats['total'] += 1
            if len(vulnerabilities) > 0:
                stats['vulnerable'] += 1
            if license_risk in ('critical', 'high'):
                stats['high_risk_licenses'] += 1
        self.session.commit()
        return stats

    def _extract_version(self, dep_data: dict) -> str | None:
        """提取版本号"""
        evidence_collected = dep_data.get('evidenceCollected', {})
        version_evidence = evidence_collected.get('versionEvidence', [])
        for evidence in version_evidence:
            if evidence.get('confidence') == 'HIGHEST':
                return evidence.get('value')
        file_name = dep_data.get('fileName', '')
        version_match = re.search('(\\d+\\.\\d+\\.\\d+)', file_name)
        if version_match:
            return version_match.group(1)
        return None

    def _extract_license(self, dep_data: dict) -> dict:
        """提取许可证信息"""
        license_str = dep_data.get('license', '')
        if not license_str:
            return {'name': 'Unknown', 'spdx_id': 'UNKNOWN', 'url': None}
        spdx_id = self._normalize_license_spdx(license_str)
        return {'name': license_str, 'spdx_id': spdx_id, 'url': None}

    def _normalize_license_spdx(self, license_str: str) -> str:
        """规范化许可证为 SPDX ID"""
        if license_str in self.LICENSE_SPDX_MAPPING:
            return self.LICENSE_SPDX_MAPPING[license_str]
        license_lower = license_str.lower()
        if 'apache' in license_lower and '2' in license_lower:
            return 'Apache-2.0'
        elif 'mit' in license_lower:
            return 'MIT'
        elif 'gpl' in license_lower and '3' in license_lower:
            return 'GPL-3.0'
        elif 'gpl' in license_lower and '2' in license_lower:
            return 'GPL-2.0'
        elif 'lgpl' in license_lower:
            return 'LGPL-3.0'
        elif 'agpl' in license_lower:
            return 'AGPL-3.0'
        elif 'bsd' in license_lower:
            return 'BSD-3-Clause'
        return 'UNKNOWN'

    def _assess_license_risk(self, spdx_id: str) -> str:
        """评估许可证风险等级"""
        rule = self.license_rules.get(spdx_id)
        if rule:
            return rule.risk_level
        if spdx_id in ('GPL-3.0', 'GPL-2.0', 'AGPL-3.0'):
            return 'critical'
        elif spdx_id in ('LGPL-3.0', 'LGPL-2.1', 'MPL-2.0'):
            return 'high'
        elif spdx_id in ('Apache-2.0', 'MIT', 'BSD-3-Clause', 'BSD-2-Clause'):
            return 'low'
        else:
            return 'unknown'

    def _detect_package_manager(self, dep_data: dict) -> str | None:
        """检测包管理器"""
        file_path = dep_data.get('filePath', '')
        if 'pom.xml' in file_path or '.jar' in file_path:
            return 'maven'
        elif 'package.json' in file_path or 'node_modules' in file_path:
            return 'npm'
        elif 'requirements.txt' in file_path or 'Pipfile' in file_path or '.whl' in file_path:
            return 'pypi'
        elif '.csproj' in file_path or 'packages.config' in file_path or '.nupkg' in file_path:
            return 'nuget'
        elif 'go.mod' in file_path or 'go.sum' in file_path:
            return 'go'
        elif 'Gemfile' in file_path or '.gem' in file_path:
            return 'rubygems'
        return None

    def _analyze_vulnerabilities(self, vulnerabilities: list[dict]) -> dict:
        """分析漏洞统计"""
        stats = {'highest_cvss': 0.0, 'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for vuln in vulnerabilities:
            cvss = self._extract_cvss_score(vuln)
            if cvss:
                stats['highest_cvss'] = max(stats['highest_cvss'], cvss)
            severity = vuln.get('severity', '').upper()
            if severity == 'CRITICAL':
                stats['critical'] += 1
            elif severity == 'HIGH':
                stats['high'] += 1
            elif severity == 'MEDIUM':
                stats['medium'] += 1
            elif severity == 'LOW':
                stats['low'] += 1
        return stats

    def _extract_cvss_score(self, vuln: dict) -> float | None:
        """提取 CVSS 评分"""
        cvssv3 = vuln.get('cvssv3', {})
        if cvssv3 and 'baseScore' in cvssv3:
            return float(cvssv3['baseScore'])
        cvssv2 = vuln.get('cvssv2', {})
        if cvssv2 and 'score' in cvssv2:
            return float(cvssv2['score'])
        return None

    def _extract_cvss_vector(self, vuln: dict) -> str | None:
        """提取 CVSS 向量"""
        cvssv3 = vuln.get('cvssv3', {})
        if cvssv3 and 'attackVector' in cvssv3:
            return cvssv3['attackVector']
        return None

PluginRegistry.register_worker('dependency_check', DependencyCheckWorker)

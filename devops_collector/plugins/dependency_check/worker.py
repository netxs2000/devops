"""
OWASP Dependency-Check Worker
采集项目的依赖清单、许可证信息和漏洞信息
"""
from typing import Dict, List, Optional
from datetime import datetime
import re

from devops_collector.core.base_worker import BaseWorker
from devops_collector.models.dependency import (
    DependencyScan, Dependency, DependencyCVE, LicenseRiskRule
)
from devops_collector.plugins.dependency_check.client import DependencyCheckClient


class DependencyCheckWorker(BaseWorker):
    """OWASP Dependency-Check 数据采集器"""
    
    SCHEMA_VERSION = "1.0.0"
    
    # 许可证 SPDX ID 映射表
    LICENSE_SPDX_MAPPING = {
        'Apache License 2.0': 'Apache-2.0',
        'Apache License, Version 2.0': 'Apache-2.0',
        'Apache 2.0': 'Apache-2.0',
        'MIT License': 'MIT',
        'The MIT License': 'MIT',
        'BSD 3-Clause': 'BSD-3-Clause',
        'BSD 2-Clause': 'BSD-2-Clause',
        'GPL-3.0': 'GPL-3.0',
        'GPL-2.0': 'GPL-2.0',
        'LGPL-3.0': 'LGPL-3.0',
        'LGPL-2.1': 'LGPL-2.1',
        'AGPL-3.0': 'AGPL-3.0',
        'MPL-2.0': 'MPL-2.0',
        'EPL-2.0': 'EPL-2.0',
    }
    
    def __init__(self, config):
        super().__init__(config)
        
        # 初始化客户端
        cli_path = config.get('dependency_check', {}).get('cli_path', 'dependency-check')
        timeout = config.get('dependency_check', {}).get('timeout', 600)
        self.client = DependencyCheckClient(cli_path, timeout)
        
        # 报告存储配置
        self.report_base_dir = config.get('dependency_check', {}).get('report_dir', '/var/lib/devops/dependency-reports')
        self.keep_reports = config.get('dependency_check', {}).get('keep_reports', True)
        self.report_retention_days = config.get('dependency_check', {}).get('report_retention_days', 90)
        
        # 确保报告目录存在
        Path(self.report_base_dir).mkdir(parents=True, exist_ok=True)
        
        # 加载许可证规则
        self.license_rules = self._load_license_rules()
        
        # 获取扫描器版本
        self.scanner_version = self.client.get_version()
    
    def _load_license_rules(self) -> Dict[str, LicenseRiskRule]:
        """加载许可证风险规则"""
        rules = {}
        try:
            with self.get_db_session() as session:
                for rule in session.query(LicenseRiskRule).filter_by(is_active=True).all():
                    if rule.license_spdx_id:
                        rules[rule.license_spdx_id] = rule
                    rules[rule.license_name] = rule
            self.logger.info(f"Loaded {len(rules)} license risk rules")
        except Exception as e:
            self.logger.error(f"Failed to load license rules: {e}")
        return rules
    
    def run_scan(self, project_id: int, project_path: str, project_name: Optional[str] = None) -> Optional[int]:
        """
        执行依赖扫描
        
        Args:
            project_id: 项目 ID
            project_path: 项目本地路径
            project_name: 项目名称
            
        Returns:
            scan_id: 扫描记录 ID
        """
        self.logger.info(f"Starting dependency scan for project {project_id}")
        
        # 创建扫描记录
        scan = DependencyScan(
            project_id=project_id,
            scan_status='in_progress',
            scanner_version=self.scanner_version
        )
        
        with self.get_db_session() as session:
            session.add(scan)
            session.commit()
            scan_id = scan.id
        
        try:
            # 使用持久化报告目录
            # 目录结构: /var/lib/devops/dependency-reports/{project_name}/{scan_id}
            if project_name:
                output_dir = f"{self.report_base_dir}/{project_name}/{scan_id}"
            else:
                output_dir = f"{self.report_base_dir}/project_{project_id}/{scan_id}"
            
            self.logger.info(f"Report will be saved to: {output_dir}")
            
            # 执行扫描
            report_path = self.client.scan_project(
                project_path=project_path,
                output_dir=output_dir,
                project_name=project_name
            )
            
            # 解析报告
            report_data = self.client.parse_report(report_path)
            
            # 保存依赖清单
            stats = self._save_dependencies(scan_id, project_id, report_data)
            
            # 更新扫描记录
            with self.get_db_session() as session:
                scan = session.query(DependencyScan).get(scan_id)
                scan.scan_status = 'completed'
                scan.report_path = report_path
                scan.raw_json = report_data
                scan.total_dependencies = stats['total']
                scan.vulnerable_dependencies = stats['vulnerable']
                scan.high_risk_licenses = stats['high_risk_licenses']
                session.commit()
            
            self.logger.info(f"Scan completed for project {project_id}, scan_id: {scan_id}")
            self.logger.info(f"Report saved at: {report_path}")
            
            return scan_id
            
        except Exception as e:
            self.logger.error(f"Scan failed for project {project_id}: {e}")
            with self.get_db_session() as session:
                scan = session.query(DependencyScan).get(scan_id)
                scan.scan_status = 'failed'
                session.commit()
            raise
    
    def import_existing_report(self, project_id: int, report_path: str, project_name: Optional[str] = None) -> Optional[int]:
        """
        导入已有的 Dependency-Check 报告
        
        Args:
            project_id: 项目 ID
            report_path: 已有报告的路径
            project_name: 项目名称
            
        Returns:
            scan_id: 扫描记录 ID
        """
        self.logger.info(f"Importing existing report: {report_path}")
        
        # 验证报告文件存在
        if not Path(report_path).exists():
            raise FileNotFoundError(f"Report file not found: {report_path}")
        
        # 创建扫描记录
        scan = DependencyScan(
            project_id=project_id,
            scan_status='in_progress',
            scanner_version=self.scanner_version
        )
        
        with self.get_db_session() as session:
            session.add(scan)
            session.commit()
            scan_id = scan.id
        
        try:
            # 解析报告
            report_data = self.client.parse_report(report_path)
            
            # 保存依赖清单
            stats = self._save_dependencies(scan_id, project_id, report_data)
            
            # 更新扫描记录
            with self.get_db_session() as session:
                scan = session.query(DependencyScan).get(scan_id)
                scan.scan_status = 'completed'
                scan.report_path = report_path
                scan.raw_json = report_data
                scan.total_dependencies = stats['total']
                scan.vulnerable_dependencies = stats['vulnerable']
                scan.high_risk_licenses = stats['high_risk_licenses']
                session.commit()
            
            self.logger.info(f"Import completed for project {project_id}, scan_id: {scan_id}")
            return scan_id
            
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            with self.get_db_session() as session:
                scan = session.query(DependencyScan).get(scan_id)
                scan.scan_status = 'failed'
                session.commit()
            raise
    
    def cleanup_old_reports(self, dry_run: bool = False) -> Dict[str, int]:
        """
        清理过期的报告文件
        
        Args:
            dry_run: 如果为 True，只列出要删除的文件，不实际删除
            
        Returns:
            统计信息: {'deleted_count': int, 'freed_space_mb': float}
        """
        from datetime import datetime, timedelta
        import shutil
        
        if self.report_retention_days == 0:
            self.logger.info("Report retention is set to 0 (永久保留), skipping cleanup")
            return {'deleted_count': 0, 'freed_space_mb': 0.0}
        
        cutoff_date = datetime.now() - timedelta(days=self.report_retention_days)
        self.logger.info(f"Cleaning up reports older than {cutoff_date}")
        
        deleted_count = 0
        freed_space = 0
        report_base_path = Path(self.report_base_dir)
        
        if not report_base_path.exists():
            self.logger.warning(f"Report directory does not exist: {self.report_base_dir}")
            return {'deleted_count': 0, 'freed_space_mb': 0.0}
        
        # 遍历所有项目目录
        for project_dir in report_base_path.iterdir():
            if not project_dir.is_dir():
                continue
            
            # 遍历每个项目的扫描目录
            for scan_dir in project_dir.iterdir():
                if not scan_dir.is_dir():
                    continue
                
                # 检查目录修改时间
                mtime = datetime.fromtimestamp(scan_dir.stat().st_mtime)
                
                if mtime < cutoff_date:
                    # 计算目录大小
                    dir_size = sum(f.stat().st_size for f in scan_dir.rglob('*') if f.is_file())
                    freed_space += dir_size
                    
                    if dry_run:
                        self.logger.info(f"[DRY RUN] Would delete: {scan_dir} ({dir_size / 1024 / 1024:.2f} MB)")
                    else:
                        shutil.rmtree(scan_dir)
                        self.logger.info(f"Deleted old report: {scan_dir} ({dir_size / 1024 / 1024:.2f} MB)")
                    
                    deleted_count += 1
        
        freed_space_mb = freed_space / 1024 / 1024
        self.logger.info(f"Cleanup completed: {deleted_count} directories, {freed_space_mb:.2f} MB freed")
        
        return {
            'deleted_count': deleted_count,
            'freed_space_mb': round(freed_space_mb, 2)
        }
    
    def _save_dependencies(self, scan_id: int, project_id: int, report_data: Dict) -> Dict:
        """保存依赖清单"""
        dependencies_data = report_data.get('dependencies', [])
        stats = {
            'total': 0,
            'vulnerable': 0,
            'high_risk_licenses': 0
        }
        
        with self.get_db_session() as session:
            for dep_data in dependencies_data:
                # 提取依赖信息
                package_name = dep_data.get('fileName', 'Unknown')
                package_version = self._extract_version(dep_data)
                
                # 提取许可证信息
                license_info = self._extract_license(dep_data)
                license_risk = self._assess_license_risk(license_info.get('spdx_id'))
                
                # 提取漏洞信息
                vulnerabilities = dep_data.get('vulnerabilities', [])
                cve_stats = self._analyze_vulnerabilities(vulnerabilities)
                
                # 创建依赖记录
                dependency = Dependency(
                    scan_id=scan_id,
                    project_id=project_id,
                    package_name=package_name,
                    package_version=package_version,
                    package_manager=self._detect_package_manager(dep_data),
                    license_name=license_info.get('name'),
                    license_spdx_id=license_info.get('spdx_id'),
                    license_url=license_info.get('url'),
                    license_risk_level=license_risk,
                    has_vulnerabilities=len(vulnerabilities) > 0,
                    highest_cvss_score=cve_stats['highest_cvss'],
                    critical_cve_count=cve_stats['critical'],
                    high_cve_count=cve_stats['high'],
                    medium_cve_count=cve_stats['medium'],
                    low_cve_count=cve_stats['low'],
                    file_path=dep_data.get('filePath'),
                    description=dep_data.get('description'),
                    raw_data=dep_data
                )
                session.add(dependency)
                session.flush()  # 获取 dependency.id
                
                # 保存 CVE 详情
                for vuln in vulnerabilities:
                    cve = DependencyCVE(
                        dependency_id=dependency.id,
                        cve_id=vuln.get('name', 'UNKNOWN'),
                        cvss_score=self._extract_cvss_score(vuln),
                        cvss_vector=self._extract_cvss_vector(vuln),
                        severity=vuln.get('severity', 'UNKNOWN'),
                        description=vuln.get('description'),
                        references=vuln.get('references', [])
                    )
                    session.add(cve)
                
                # 统计
                stats['total'] += 1
                if len(vulnerabilities) > 0:
                    stats['vulnerable'] += 1
                if license_risk in ('critical', 'high'):
                    stats['high_risk_licenses'] += 1
            
            session.commit()
        
        return stats
    
    def _extract_version(self, dep_data: Dict) -> Optional[str]:
        """提取版本号"""
        # 优先从 evidenceCollected 中提取
        evidence_collected = dep_data.get('evidenceCollected', {})
        version_evidence = evidence_collected.get('versionEvidence', [])
        
        for evidence in version_evidence:
            if evidence.get('confidence') == 'HIGHEST':
                return evidence.get('value')
        
        # 从文件名中提取（简化版本）
        file_name = dep_data.get('fileName', '')
        # 匹配常见的版本号模式: x.y.z
        version_match = re.search(r'(\d+\.\d+\.\d+)', file_name)
        if version_match:
            return version_match.group(1)
        
        return None
    
    def _extract_license(self, dep_data: Dict) -> Dict:
        """提取许可证信息"""
        license_str = dep_data.get('license', '')
        
        if not license_str:
            return {
                'name': 'Unknown',
                'spdx_id': 'UNKNOWN',
                'url': None
            }
        
        # 规范化为 SPDX ID
        spdx_id = self._normalize_license_spdx(license_str)
        
        return {
            'name': license_str,
            'spdx_id': spdx_id,
            'url': None
        }
    
    def _normalize_license_spdx(self, license_str: str) -> str:
        """规范化许可证为 SPDX ID"""
        # 直接匹配
        if license_str in self.LICENSE_SPDX_MAPPING:
            return self.LICENSE_SPDX_MAPPING[license_str]
        
        # 模糊匹配
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
        
        # 默认规则
        if spdx_id in ('GPL-3.0', 'GPL-2.0', 'AGPL-3.0'):
            return 'critical'
        elif spdx_id in ('LGPL-3.0', 'LGPL-2.1', 'MPL-2.0'):
            return 'high'
        elif spdx_id in ('Apache-2.0', 'MIT', 'BSD-3-Clause', 'BSD-2-Clause'):
            return 'low'
        else:
            return 'unknown'
    
    def _detect_package_manager(self, dep_data: Dict) -> Optional[str]:
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
    
    def _analyze_vulnerabilities(self, vulnerabilities: List[Dict]) -> Dict:
        """分析漏洞统计"""
        stats = {
            'highest_cvss': 0.0,
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
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
    
    def _extract_cvss_score(self, vuln: Dict) -> Optional[float]:
        """提取 CVSS 评分"""
        # 优先使用 CVSSv3
        cvssv3 = vuln.get('cvssv3', {})
        if cvssv3 and 'baseScore' in cvssv3:
            return float(cvssv3['baseScore'])
        
        # 回退到 CVSSv2
        cvssv2 = vuln.get('cvssv2', {})
        if cvssv2 and 'score' in cvssv2:
            return float(cvssv2['score'])
        
        return None
    
    def _extract_cvss_vector(self, vuln: Dict) -> Optional[str]:
        """提取 CVSS 向量"""
        cvssv3 = vuln.get('cvssv3', {})
        if cvssv3 and 'attackVector' in cvssv3:
            return cvssv3['attackVector']
        
        return None

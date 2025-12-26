# OWASP Dependency-Check 集成方案

## 概述

本文档详细说明如何将 OWASP Dependency-Check 集成到 DevOps Data Collector 中，实现开源许可证合规性扫描和漏洞管理。

---

## 1. 数据模型设计

### 1.1 依赖扫描记录表 (`dependency_scans`)

存储每次依赖扫描的元数据。

```sql
CREATE TABLE dependency_scans (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    scan_date TIMESTAMP NOT NULL DEFAULT NOW(),
    scanner_name VARCHAR(50) NOT NULL DEFAULT 'OWASP Dependency-Check',
    scanner_version VARCHAR(20),
    total_dependencies INTEGER DEFAULT 0,
    vulnerable_dependencies INTEGER DEFAULT 0,
    high_risk_licenses INTEGER DEFAULT 0,
    scan_status VARCHAR(20) DEFAULT 'completed',  -- completed, failed, in_progress
    report_path TEXT,  -- 报告文件路径
    raw_json JSONB,  -- 原始 JSON 报告
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dependency_scans_project ON dependency_scans(project_id);
CREATE INDEX idx_dependency_scans_date ON dependency_scans(scan_date);
```

### 1.2 依赖清单表 (`dependencies`)

存储项目的依赖清单及其许可证信息。

```sql
CREATE TABLE dependencies (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER NOT NULL REFERENCES dependency_scans(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    
    -- 依赖基本信息
    package_name VARCHAR(500) NOT NULL,
    package_version VARCHAR(100),
    package_manager VARCHAR(50),  -- maven, npm, pypi, nuget, etc.
    dependency_type VARCHAR(20) DEFAULT 'direct',  -- direct, transitive
    
    -- 许可证信息
    license_name VARCHAR(200),
    license_spdx_id VARCHAR(100),  -- SPDX 标准许可证 ID
    license_url TEXT,
    license_risk_level VARCHAR(20),  -- critical, high, medium, low, unknown
    
    -- 漏洞信息
    has_vulnerabilities BOOLEAN DEFAULT FALSE,
    highest_cvss_score FLOAT,
    critical_cve_count INTEGER DEFAULT 0,
    high_cve_count INTEGER DEFAULT 0,
    medium_cve_count INTEGER DEFAULT 0,
    low_cve_count INTEGER DEFAULT 0,
    
    -- 元数据
    file_path TEXT,  -- 依赖声明文件路径 (如 pom.xml, package.json)
    description TEXT,
    homepage_url TEXT,
    raw_data JSONB,  -- 原始数据备份
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(scan_id, package_name, package_version)
);

CREATE INDEX idx_dependencies_scan ON dependencies(scan_id);
CREATE INDEX idx_dependencies_project ON dependencies(project_id);
CREATE INDEX idx_dependencies_license_risk ON dependencies(license_risk_level);
CREATE INDEX idx_dependencies_vulnerabilities ON dependencies(has_vulnerabilities);
```

### 1.3 CVE 漏洞详情表 (`dependency_cves`)

存储依赖的 CVE 漏洞详情。

```sql
CREATE TABLE dependency_cves (
    id SERIAL PRIMARY KEY,
    dependency_id INTEGER NOT NULL REFERENCES dependencies(id) ON DELETE CASCADE,
    
    -- CVE 信息
    cve_id VARCHAR(50) NOT NULL,  -- CVE-2023-12345
    cvss_score FLOAT,
    cvss_vector VARCHAR(200),
    severity VARCHAR(20),  -- CRITICAL, HIGH, MEDIUM, LOW
    
    -- 漏洞描述
    description TEXT,
    published_date DATE,
    last_modified_date DATE,
    
    -- 修复建议
    fixed_version VARCHAR(100),
    remediation TEXT,
    
    -- 引用链接
    references JSONB,  -- [{url: "...", source: "NVD"}]
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(dependency_id, cve_id)
);

CREATE INDEX idx_dependency_cves_dependency ON dependency_cves(dependency_id);
CREATE INDEX idx_dependency_cves_severity ON dependency_cves(severity);
CREATE INDEX idx_dependency_cves_score ON dependency_cves(cvss_score);
```

### 1.4 许可证风险规则表 (`license_risk_rules`)

定义许可证的风险等级规则。

```sql
CREATE TABLE license_risk_rules (
    id SERIAL PRIMARY KEY,
    license_name VARCHAR(200) NOT NULL UNIQUE,
    license_spdx_id VARCHAR(100),
    risk_level VARCHAR(20) NOT NULL,  -- critical, high, medium, low
    is_copyleft BOOLEAN DEFAULT FALSE,  -- 是否为传染性许可证
    commercial_use_allowed BOOLEAN DEFAULT TRUE,
    modification_allowed BOOLEAN DEFAULT TRUE,
    distribution_allowed BOOLEAN DEFAULT TRUE,
    patent_grant BOOLEAN DEFAULT FALSE,
    description TEXT,
    policy_notes TEXT,  -- 企业政策备注
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 预置常见许可证规则
INSERT INTO license_risk_rules (license_name, license_spdx_id, risk_level, is_copyleft, commercial_use_allowed, description) VALUES
('GNU General Public License v3.0', 'GPL-3.0', 'critical', TRUE, FALSE, '强传染性许可证，要求衍生作品也必须开源'),
('GNU Affero General Public License v3.0', 'AGPL-3.0', 'critical', TRUE, FALSE, '最严格的传染性许可证，网络服务也需开源'),
('GNU General Public License v2.0', 'GPL-2.0', 'critical', TRUE, FALSE, '传染性许可证，商业使用受限'),
('GNU Lesser General Public License v3.0', 'LGPL-3.0', 'high', TRUE, TRUE, '弱传染性，动态链接可接受'),
('GNU Lesser General Public License v2.1', 'LGPL-2.1', 'high', TRUE, TRUE, '弱传染性，动态链接可接受'),
('Mozilla Public License 2.0', 'MPL-2.0', 'medium', TRUE, TRUE, '文件级传染性'),
('Eclipse Public License 2.0', 'EPL-2.0', 'medium', TRUE, TRUE, '弱传染性'),
('Apache License 2.0', 'Apache-2.0', 'low', FALSE, TRUE, '商业友好，提供专利授权'),
('MIT License', 'MIT', 'low', FALSE, TRUE, '最宽松的许可证之一'),
('BSD 3-Clause License', 'BSD-3-Clause', 'low', FALSE, TRUE, '商业友好'),
('BSD 2-Clause License', 'BSD-2-Clause', 'low', FALSE, TRUE, '商业友好'),
('ISC License', 'ISC', 'low', FALSE, TRUE, '类似 MIT'),
('Unlicense', 'Unlicense', 'low', FALSE, TRUE, '公共领域'),
('Creative Commons Zero v1.0', 'CC0-1.0', 'low', FALSE, TRUE, '公共领域'),
('Unknown', 'UNKNOWN', 'high', FALSE, FALSE, '未知许可证，需人工审核');
```

---

## 2. OWASP Dependency-Check 采集器实现

### 2.1 Worker 实现 (`dependency_check_worker.py`)

```python
"""
OWASP Dependency-Check Worker
采集项目的依赖清单、许可证信息和漏洞信息
"""
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from devops_collector.core.base_worker import BaseWorker
from devops_collector.models import (
    DependencyScan, Dependency, DependencyCVE, LicenseRiskRule
)


class DependencyCheckWorker(BaseWorker):
    """OWASP Dependency-Check 数据采集器"""
    
    SCHEMA_VERSION = "1.0.0"
    
    def __init__(self, config):
        super().__init__(config)
        self.dependency_check_path = config.get('dependency_check', {}).get('cli_path', 'dependency-check')
        self.scan_timeout = config.get('dependency_check', {}).get('timeout', 600)
        self.license_rules = self._load_license_rules()
    
    def _load_license_rules(self) -> Dict[str, LicenseRiskRule]:
        """加载许可证风险规则"""
        rules = {}
        with self.get_db_session() as session:
            for rule in session.query(LicenseRiskRule).filter_by(is_active=True).all():
                rules[rule.license_spdx_id] = rule
                rules[rule.license_name] = rule
        return rules
    
    def run_scan(self, project_id: int, project_path: str) -> Optional[int]:
        """
        执行依赖扫描
        
        Args:
            project_id: 项目 ID
            project_path: 项目本地路径
            
        Returns:
            scan_id: 扫描记录 ID
        """
        self.logger.info(f"Starting dependency scan for project {project_id}")
        
        # 创建扫描记录
        scan = DependencyScan(
            project_id=project_id,
            scan_status='in_progress'
        )
        
        with self.get_db_session() as session:
            session.add(scan)
            session.commit()
            scan_id = scan.id
        
        try:
            # 执行 OWASP Dependency-Check
            report_path = self._run_dependency_check(project_path, scan_id)
            
            # 解析报告
            report_data = self._parse_report(report_path)
            
            # 保存依赖清单
            self._save_dependencies(scan_id, project_id, report_data)
            
            # 更新扫描记录
            with self.get_db_session() as session:
                scan = session.query(DependencyScan).get(scan_id)
                scan.scan_status = 'completed'
                scan.report_path = report_path
                scan.raw_json = report_data
                scan.total_dependencies = len(report_data.get('dependencies', []))
                scan.vulnerable_dependencies = sum(
                    1 for dep in report_data.get('dependencies', [])
                    if dep.get('vulnerabilities')
                )
                session.commit()
            
            self.logger.info(f"Scan completed for project {project_id}, scan_id: {scan_id}")
            return scan_id
            
        except Exception as e:
            self.logger.error(f"Scan failed for project {project_id}: {e}")
            with self.get_db_session() as session:
                scan = session.query(DependencyScan).get(scan_id)
                scan.scan_status = 'failed'
                session.commit()
            raise
    
    def _run_dependency_check(self, project_path: str, scan_id: int) -> str:
        """执行 OWASP Dependency-Check CLI"""
        output_dir = Path(f"/tmp/dependency-check-reports/{scan_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.dependency_check_path,
            '--scan', project_path,
            '--format', 'JSON',
            '--out', str(output_dir),
            '--prettyPrint',
            '--enableExperimental',  # 启用实验性分析器
        ]
        
        self.logger.info(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            timeout=self.scan_timeout,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Dependency-Check failed: {result.stderr}")
        
        report_path = output_dir / "dependency-check-report.json"
        if not report_path.exists():
            raise FileNotFoundError(f"Report not found: {report_path}")
        
        return str(report_path)
    
    def _parse_report(self, report_path: str) -> Dict:
        """解析 JSON 报告"""
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_dependencies(self, scan_id: int, project_id: int, report_data: Dict):
        """保存依赖清单"""
        dependencies_data = report_data.get('dependencies', [])
        
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
                        cve_id=vuln.get('name'),
                        cvss_score=vuln.get('cvssv3', {}).get('baseScore'),
                        cvss_vector=vuln.get('cvssv3', {}).get('attackVector'),
                        severity=vuln.get('severity'),
                        description=vuln.get('description'),
                        references=vuln.get('references', [])
                    )
                    session.add(cve)
            
            session.commit()
    
    def _extract_version(self, dep_data: Dict) -> Optional[str]:
        """提取版本号"""
        # 优先从 evidenceCollected 中提取
        for evidence in dep_data.get('evidenceCollected', {}).get('versionEvidence', []):
            if evidence.get('confidence') == 'HIGHEST':
                return evidence.get('value')
        
        # 从文件名中提取
        file_name = dep_data.get('fileName', '')
        # 简化逻辑，实际需要更复杂的正则匹配
        return None
    
    def _extract_license(self, dep_data: Dict) -> Dict:
        """提取许可证信息"""
        license_data = dep_data.get('license', '')
        if not license_data:
            return {'name': 'Unknown', 'spdx_id': 'UNKNOWN', 'url': None}
        
        # 简化逻辑，实际需要解析复杂的许可证字符串
        return {
            'name': license_data,
            'spdx_id': self._normalize_license_spdx(license_data),
            'url': None
        }
    
    def _normalize_license_spdx(self, license_str: str) -> str:
        """规范化许可证为 SPDX ID"""
        # 简化映射，实际需要完整的映射表
        mapping = {
            'Apache License 2.0': 'Apache-2.0',
            'MIT License': 'MIT',
            'GPL-3.0': 'GPL-3.0',
            # ... 更多映射
        }
        return mapping.get(license_str, 'UNKNOWN')
    
    def _assess_license_risk(self, spdx_id: str) -> str:
        """评估许可证风险等级"""
        rule = self.license_rules.get(spdx_id)
        if rule:
            return rule.risk_level
        return 'unknown'
    
    def _detect_package_manager(self, dep_data: Dict) -> Optional[str]:
        """检测包管理器"""
        file_path = dep_data.get('filePath', '')
        if 'pom.xml' in file_path:
            return 'maven'
        elif 'package.json' in file_path:
            return 'npm'
        elif 'requirements.txt' in file_path or 'Pipfile' in file_path:
            return 'pypi'
        elif '.csproj' in file_path or 'packages.config' in file_path:
            return 'nuget'
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
            cvss = vuln.get('cvssv3', {}).get('baseScore', 0)
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
```

---

## 3. 配置文件 (`config.ini`)

```ini
[dependency_check]
# OWASP Dependency-Check CLI 路径
cli_path = /usr/local/bin/dependency-check.sh

# 扫描超时时间（秒）
timeout = 600

# 是否启用自动扫描
auto_scan_enabled = true

# 扫描频率（天）
scan_frequency_days = 7

# 是否扫描传递依赖
scan_transitive = true
```

---

## 4. 增强的许可证合规性分析视图

```sql
-- 替换原有的 view_compliance_oss_license_risk
CREATE OR REPLACE VIEW view_compliance_oss_license_risk_enhanced AS
WITH latest_scans AS (
    SELECT DISTINCT ON (project_id)
        id as scan_id,
        project_id,
        scan_date,
        total_dependencies
    FROM dependency_scans
    WHERE scan_status = 'completed'
    ORDER BY project_id, scan_date DESC
),
dependency_risk_summary AS (
    SELECT 
        d.project_id,
        d.license_risk_level,
        COUNT(*) as dependency_count,
        SUM(d.critical_cve_count) as total_critical_cves,
        SUM(d.high_cve_count) as total_high_cves
    FROM dependencies d
    JOIN latest_scans ls ON d.scan_id = ls.scan_id
    GROUP BY d.project_id, d.license_risk_level
)
SELECT 
    p.name as project_name,
    g.name as group_name,
    ls.scan_date as last_scan_date,
    ls.total_dependencies,
    -- 许可证风险统计
    COALESCE(SUM(CASE WHEN drs.license_risk_level = 'critical' THEN drs.dependency_count END), 0) as critical_risk_count,
    COALESCE(SUM(CASE WHEN drs.license_risk_level = 'high' THEN drs.dependency_count END), 0) as high_risk_count,
    COALESCE(SUM(CASE WHEN drs.license_risk_level = 'medium' THEN drs.dependency_count END), 0) as medium_risk_count,
    COALESCE(SUM(CASE WHEN drs.license_risk_level = 'unknown' THEN drs.dependency_count END), 0) as unknown_license_count,
    -- 漏洞统计
    COALESCE(SUM(drs.total_critical_cves), 0) as total_critical_cves,
    COALESCE(SUM(drs.total_high_cves), 0) as total_high_cves,
    -- 高风险许可证占比
    ROUND(
        COALESCE(SUM(CASE WHEN drs.license_risk_level IN ('critical', 'high') THEN drs.dependency_count END), 0)::numeric 
        / NULLIF(ls.total_dependencies, 0) * 100, 2
    ) as high_risk_rate_pct,
    -- 合规状态
    CASE 
        WHEN COALESCE(SUM(CASE WHEN drs.license_risk_level = 'critical' THEN drs.dependency_count END), 0) > 0 
        THEN 'Critical: GPL/AGPL Detected'
        WHEN COALESCE(SUM(CASE WHEN drs.license_risk_level = 'high' THEN drs.dependency_count END), 0) > 5 
        THEN 'High Risk: Multiple LGPL/MPL'
        WHEN COALESCE(SUM(CASE WHEN drs.license_risk_level = 'unknown' THEN drs.dependency_count END), 0)::numeric 
             / NULLIF(ls.total_dependencies, 0) > 0.3 
        THEN 'Warning: Many Unknown Licenses'
        WHEN COALESCE(SUM(drs.total_critical_cves), 0) > 0
        THEN 'Critical: Security Vulnerabilities'
        ELSE 'Low Risk'
    END as compliance_status
FROM projects p
JOIN gitlab_groups g ON p.group_id = g.id
JOIN latest_scans ls ON p.id = ls.project_id
LEFT JOIN dependency_risk_summary drs ON p.id = drs.project_id
WHERE p.archived = false
GROUP BY p.name, g.name, ls.scan_date, ls.total_dependencies
ORDER BY 
    CASE 
        WHEN COALESCE(SUM(CASE WHEN drs.license_risk_level = 'critical' THEN drs.dependency_count END), 0) > 0 THEN 1
        WHEN COALESCE(SUM(drs.total_critical_cves), 0) > 0 THEN 2
        ELSE 3
    END,
    high_risk_rate_pct DESC;
```

---

## 5. 使用指南

### 5.1 安装 OWASP Dependency-Check

```bash
# 下载最新版本
wget https://github.com/jeremylong/DependencyCheck/releases/download/v8.4.0/dependency-check-8.4.0-release.zip

# 解压
unzip dependency-check-8.4.0-release.zip

# 配置环境变量
export PATH=$PATH:/path/to/dependency-check/bin
```

### 5.2 运行扫描

```python
from devops_collector.plugins.dependency_check import DependencyCheckWorker

# 初始化 Worker
worker = DependencyCheckWorker(config)

# 扫描项目
scan_id = worker.run_scan(
    project_id=123,
    project_path='/path/to/project'
)
```

### 5.3 查询结果

```sql
-- 查看项目的许可证合规性
SELECT * FROM view_compliance_oss_license_risk_enhanced
WHERE project_name = 'my-project';

-- 查看高风险依赖详情
SELECT 
    d.package_name,
    d.package_version,
    d.license_name,
    d.license_risk_level,
    d.critical_cve_count,
    d.high_cve_count
FROM dependencies d
JOIN dependency_scans ds ON d.scan_id = ds.id
WHERE ds.project_id = 123
  AND d.license_risk_level IN ('critical', 'high')
ORDER BY d.critical_cve_count DESC, d.high_cve_count DESC;
```

---

## 6. 核心优势

✅ **完整的许可证信息**: 基于 OWASP Dependency-Check 的 SPDX 标准化许可证识别  
✅ **漏洞与许可证双重扫描**: 同时识别安全漏洞和许可证风险  
✅ **自动化风险评级**: 基于预置规则自动评估许可证风险等级  
✅ **历史趋势分析**: 支持多次扫描的历史对比  
✅ **合规性报告**: 为法务部门提供详细的许可证清单

---

## 7. 下一步扩展

1. **集成 ClearlyDefined API**: 获取更准确的许可证信息
2. **自动化修复建议**: 基于 CVE 信息提供升级建议
3. **许可证冲突检测**: 识别同一项目中的许可证冲突
4. **SBOM 生成**: 生成符合 CycloneDX/SPDX 标准的 SBOM 文件

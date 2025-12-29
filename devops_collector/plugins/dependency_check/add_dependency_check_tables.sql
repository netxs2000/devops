-- ============================================================
-- OWASP Dependency-Check Integration - Database Migration
-- 此脚本用于创建依赖扫描相关的数据表
-- ============================================================

-- 1. 依赖扫描记录表
CREATE TABLE IF NOT EXISTS dependency_scans (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scan_date TIMESTAMP NOT NULL DEFAULT NOW(),
    scanner_name VARCHAR(50) NOT NULL DEFAULT 'OWASP Dependency-Check',
    scanner_version VARCHAR(20),
    total_dependencies INTEGER DEFAULT 0,
    vulnerable_dependencies INTEGER DEFAULT 0,
    high_risk_licenses INTEGER DEFAULT 0,
    scan_status VARCHAR(20) DEFAULT 'completed',  -- completed, failed, in_progress
    report_path TEXT,
    raw_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dependency_scans_project ON dependency_scans(project_id);
CREATE INDEX IF NOT EXISTS idx_dependency_scans_date ON dependency_scans(scan_date);
CREATE INDEX IF NOT EXISTS idx_dependency_scans_status ON dependency_scans(scan_status);

COMMENT ON TABLE dependency_scans IS '依赖扫描记录表，存储每次 OWASP Dependency-Check 扫描的元数据';
COMMENT ON COLUMN dependency_scans.scan_status IS '扫描状态: completed(完成), failed(失败), in_progress(进行中)';


-- 2. 许可证风险规则表
CREATE TABLE IF NOT EXISTS license_risk_rules (
    id SERIAL PRIMARY KEY,
    license_name VARCHAR(200) NOT NULL UNIQUE,
    license_spdx_id VARCHAR(100),
    risk_level VARCHAR(20) NOT NULL,  -- critical, high, medium, low
    is_copyleft BOOLEAN DEFAULT FALSE,
    commercial_use_allowed BOOLEAN DEFAULT TRUE,
    modification_allowed BOOLEAN DEFAULT TRUE,
    distribution_allowed BOOLEAN DEFAULT TRUE,
    patent_grant BOOLEAN DEFAULT FALSE,
    description TEXT,
    policy_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_license_risk_rules_spdx ON license_risk_rules(license_spdx_id);
CREATE INDEX IF NOT EXISTS idx_license_risk_rules_level ON license_risk_rules(risk_level);

COMMENT ON TABLE license_risk_rules IS '许可证风险规则表，定义各类开源许可证的风险等级和使用限制';
COMMENT ON COLUMN license_risk_rules.is_copyleft IS '是否为传染性许可证（如 GPL）';


-- 3. 依赖清单表
CREATE TABLE IF NOT EXISTS dependencies (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER NOT NULL REFERENCES dependency_scans(id) ON DELETE CASCADE,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- 依赖基本信息
    package_name VARCHAR(500) NOT NULL,
    package_version VARCHAR(100),
    package_manager VARCHAR(50),  -- maven, npm, pypi, nuget, etc.
    dependency_type VARCHAR(20) DEFAULT 'direct',  -- direct, transitive
    
    -- 许可证信息
    license_name VARCHAR(200),
    license_spdx_id VARCHAR(100),
    license_url TEXT,
    license_risk_level VARCHAR(20),
    
    -- 漏洞信息
    has_vulnerabilities BOOLEAN DEFAULT FALSE,
    highest_cvss_score FLOAT,
    critical_cve_count INTEGER DEFAULT 0,
    high_cve_count INTEGER DEFAULT 0,
    medium_cve_count INTEGER DEFAULT 0,
    low_cve_count INTEGER DEFAULT 0,
    
    -- 元数据
    file_path TEXT,
    description TEXT,
    homepage_url TEXT,
    raw_data JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(scan_id, package_name, package_version)
);

CREATE INDEX IF NOT EXISTS idx_dependencies_scan ON dependencies(scan_id);
CREATE INDEX IF NOT EXISTS idx_dependencies_project ON dependencies(project_id);
CREATE INDEX IF NOT EXISTS idx_dependencies_license_risk ON dependencies(license_risk_level);
CREATE INDEX IF NOT EXISTS idx_dependencies_vulnerabilities ON dependencies(has_vulnerabilities);
CREATE INDEX IF NOT EXISTS idx_dependencies_package_manager ON dependencies(package_manager);

COMMENT ON TABLE dependencies IS '依赖清单表，存储项目的依赖包及其许可证和漏洞信息';
COMMENT ON COLUMN dependencies.dependency_type IS '依赖类型: direct(直接依赖), transitive(传递依赖)';


-- 4. CVE 漏洞详情表
CREATE TABLE IF NOT EXISTS dependency_cves (
    id SERIAL PRIMARY KEY,
    dependency_id INTEGER NOT NULL REFERENCES dependencies(id) ON DELETE CASCADE,
    
    -- CVE 信息
    cve_id VARCHAR(50) NOT NULL,
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
    references JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(dependency_id, cve_id)
);

CREATE INDEX IF NOT EXISTS idx_dependency_cves_dependency ON dependency_cves(dependency_id);
CREATE INDEX IF NOT EXISTS idx_dependency_cves_severity ON dependency_cves(severity);
CREATE INDEX IF NOT EXISTS idx_dependency_cves_score ON dependency_cves(cvss_score);
CREATE INDEX IF NOT EXISTS idx_dependency_cves_cve_id ON dependency_cves(cve_id);

COMMENT ON TABLE dependency_cves IS 'CVE 漏洞详情表，存储依赖包的安全漏洞信息';
COMMENT ON COLUMN dependency_cves.cvss_score IS 'CVSS 评分 (0-10)，分数越高风险越大';


-- 5. 预置常见许可证规则
INSERT INTO license_risk_rules (license_name, license_spdx_id, risk_level, is_copyleft, commercial_use_allowed, description) VALUES
('GNU General Public License v3.0', 'GPL-3.0', 'critical', TRUE, FALSE, '强传染性许可证，要求衍生作品也必须开源'),
('GNU Affero General Public License v3.0', 'AGPL-3.0', 'critical', TRUE, FALSE, '最严格的传染性许可证，网络服务也需开源'),
('GNU General Public License v2.0', 'GPL-2.0', 'critical', TRUE, FALSE, '传染性许可证，商业使用受限'),
('GNU Lesser General Public License v3.0', 'LGPL-3.0', 'high', TRUE, TRUE, '弱传染性，动态链接可接受'),
('GNU Lesser General Public License v2.1', 'LGPL-2.1', 'high', TRUE, TRUE, '弱传染性，动态链接可接受'),
('Mozilla Public License 2.0', 'MPL-2.0', 'medium', TRUE, TRUE, '文件级传染性'),
('Eclipse Public License 2.0', 'EPL-2.0', 'medium', TRUE, TRUE, '弱传染性'),
('Common Development and Distribution License 1.0', 'CDDL-1.0', 'medium', TRUE, TRUE, '弱传染性'),
('Apache License 2.0', 'Apache-2.0', 'low', FALSE, TRUE, '商业友好，提供专利授权'),
('MIT License', 'MIT', 'low', FALSE, TRUE, '最宽松的许可证之一'),
('BSD 3-Clause License', 'BSD-3-Clause', 'low', FALSE, TRUE, '商业友好'),
('BSD 2-Clause License', 'BSD-2-Clause', 'low', FALSE, TRUE, '商业友好'),
('ISC License', 'ISC', 'low', FALSE, TRUE, '类似 MIT'),
('Unlicense', 'Unlicense', 'low', FALSE, TRUE, '公共领域'),
('Creative Commons Zero v1.0', 'CC0-1.0', 'low', FALSE, TRUE, '公共领域'),
('Unknown', 'UNKNOWN', 'high', FALSE, FALSE, '未知许可证，需人工审核')
ON CONFLICT (license_name) DO NOTHING;


-- 6. 创建增强的许可证合规性分析视图
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

COMMENT ON VIEW view_compliance_oss_license_risk_enhanced IS '增强的开源许可证合规性分析视图，基于 OWASP Dependency-Check 扫描结果';

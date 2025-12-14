-- SonarQube 代码质量分析视图
-- 用于 BI 可视化和质量报告

-- ============================================
-- 1. 项目代码质量评分卡 (最新快照)
-- ============================================
CREATE OR REPLACE VIEW view_sonar_quality_scorecard AS
SELECT
    sp.key as project_key,
    sp.name as project_name,
    sp.gitlab_project_id,
    gp.name as gitlab_project_name,
    gp.department,
    sm.analysis_date,
    
    -- 代码规模
    sm.ncloc as lines_of_code,
    
    -- 核心指标
    sm.coverage,
    sm.bugs,
    sm.vulnerabilities,
    sm.code_smells,
    sm.duplicated_lines_density as duplication_rate,
    sm.sqale_index / 60 as tech_debt_hours,
    sm.complexity,
    
    -- 评级 (A-E)
    sm.reliability_rating,
    sm.security_rating,
    sm.sqale_rating as maintainability_rating,
    sm.quality_gate_status,
    
    -- 综合质量评分 (A=5, B=4, C=3, D=2, E=1)
    (
        (CASE sm.reliability_rating WHEN 'A' THEN 5 WHEN 'B' THEN 4 WHEN 'C' THEN 3 WHEN 'D' THEN 2 ELSE 1 END) +
        (CASE sm.security_rating WHEN 'A' THEN 5 WHEN 'B' THEN 4 WHEN 'C' THEN 3 WHEN 'D' THEN 2 ELSE 1 END) +
        (CASE sm.sqale_rating WHEN 'A' THEN 5 WHEN 'B' THEN 4 WHEN 'C' THEN 3 WHEN 'D' THEN 2 ELSE 1 END)
    ) / 3.0 as quality_score
    
FROM sonar_measures sm
JOIN sonar_projects sp ON sm.project_id = sp.id
LEFT JOIN projects gp ON sp.gitlab_project_id = gp.id
WHERE sm.analysis_date = (
    SELECT MAX(analysis_date) FROM sonar_measures WHERE project_id = sm.project_id
);

-- ============================================
-- 2. 代码质量趋势 (按月汇总)
-- ============================================
CREATE OR REPLACE VIEW view_sonar_quality_trend AS
SELECT
    sp.key as project_key,
    sp.name as project_name,
    DATE_TRUNC('month', sm.analysis_date) as month,
    
    -- 各指标月均值
    AVG(sm.coverage) as avg_coverage,
    AVG(sm.bugs) as avg_bugs,
    AVG(sm.vulnerabilities) as avg_vulnerabilities,
    AVG(sm.code_smells) as avg_code_smells,
    AVG(sm.duplicated_lines_density) as avg_duplication_rate,
    AVG(sm.sqale_index) / 60 as avg_tech_debt_hours,
    
    -- 最新代码行数
    MAX(sm.ncloc) as max_lines_of_code,
    
    -- 分析次数
    COUNT(*) as analysis_count
    
FROM sonar_measures sm
JOIN sonar_projects sp ON sm.project_id = sp.id
GROUP BY sp.key, sp.name, DATE_TRUNC('month', sm.analysis_date)
ORDER BY sp.key, month;

-- ============================================
-- 3. 问题分布统计 (按类型/严重级别)
-- ============================================
CREATE OR REPLACE VIEW view_sonar_issue_distribution AS
SELECT
    sp.key as project_key,
    sp.name as project_name,
    si.type,
    si.severity,
    COUNT(*) as issue_count,
    
    -- 按类型统计修复工时
    SUM(
        CASE 
            WHEN si.effort LIKE '%h' THEN CAST(REPLACE(si.effort, 'h', '') AS INTEGER) * 60
            WHEN si.effort LIKE '%min' THEN CAST(REPLACE(si.effort, 'min', '') AS INTEGER)
            ELSE 0
        END
    ) as total_effort_minutes
    
FROM sonar_issues si
JOIN sonar_projects sp ON si.project_id = sp.id
WHERE si.status NOT IN ('CLOSED', 'RESOLVED')
GROUP BY sp.key, sp.name, si.type, si.severity
ORDER BY sp.key, issue_count DESC;

-- ============================================
-- 4. 部门代码质量对比
-- ============================================
CREATE OR REPLACE VIEW view_sonar_dept_quality AS
SELECT
    gp.department,
    
    -- 项目统计
    COUNT(DISTINCT sp.id) as project_count,
    SUM(sm.ncloc) as total_lines_of_code,
    
    -- 质量指标均值
    AVG(sm.coverage) as avg_coverage,
    AVG(sm.bugs) as avg_bugs,
    AVG(sm.vulnerabilities) as avg_vulnerabilities,
    AVG(sm.code_smells) as avg_code_smells,
    SUM(sm.sqale_index) / 60 as total_tech_debt_hours,
    
    -- Bug 密度 (每千行代码)
    CASE 
        WHEN SUM(sm.ncloc) > 0 
        THEN SUM(sm.bugs) * 1000.0 / SUM(sm.ncloc) 
        ELSE 0 
    END as bug_density,
    
    -- 通过质量门禁的项目比例
    SUM(CASE WHEN sm.quality_gate_status = 'OK' THEN 1 ELSE 0 END)::FLOAT / 
        NULLIF(COUNT(*), 0) * 100 as quality_gate_pass_rate
    
FROM sonar_measures sm
JOIN sonar_projects sp ON sm.project_id = sp.id
JOIN projects gp ON sp.gitlab_project_id = gp.id
WHERE sm.analysis_date = (
    SELECT MAX(analysis_date) FROM sonar_measures WHERE project_id = sm.project_id
)
AND gp.department IS NOT NULL
GROUP BY gp.department
ORDER BY avg_coverage DESC;

-- ============================================
-- 5. 高风险项目清单
-- ============================================
CREATE OR REPLACE VIEW view_sonar_high_risk_projects AS
SELECT
    sp.key as project_key,
    sp.name as project_name,
    gp.department,
    sm.analysis_date,
    
    sm.bugs,
    sm.vulnerabilities,
    sm.reliability_rating,
    sm.security_rating,
    sm.quality_gate_status,
    
    -- 风险评分 (越高越危险)
    (
        sm.bugs * 2 +                    -- Bug 权重 2
        sm.vulnerabilities * 5 +         -- 漏洞权重 5
        (CASE sm.reliability_rating WHEN 'E' THEN 20 WHEN 'D' THEN 10 WHEN 'C' THEN 5 ELSE 0 END) +
        (CASE sm.security_rating WHEN 'E' THEN 30 WHEN 'D' THEN 15 WHEN 'C' THEN 5 ELSE 0 END) +
        (CASE sm.quality_gate_status WHEN 'ERROR' THEN 20 WHEN 'WARN' THEN 10 ELSE 0 END)
    ) as risk_score
    
FROM sonar_measures sm
JOIN sonar_projects sp ON sm.project_id = sp.id
LEFT JOIN projects gp ON sp.gitlab_project_id = gp.id
WHERE sm.analysis_date = (
    SELECT MAX(analysis_date) FROM sonar_measures WHERE project_id = sm.project_id
)
ORDER BY risk_score DESC;

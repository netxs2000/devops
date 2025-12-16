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
    sm.files,
    sm.lines,
    sm.ncloc,
    sm.classes,
    sm.functions,
    sm.statements,
    
    -- 核心指标
    sm.coverage,
    sm.bugs,
    sm.bugs_blocker,
    sm.bugs_critical,
    sm.bugs_major,
    sm.bugs_minor,
    sm.bugs_info,
    
    sm.vulnerabilities,
    sm.vulnerabilities_blocker,
    sm.vulnerabilities_critical,
    sm.vulnerabilities_major,
    sm.vulnerabilities_minor,
    sm.vulnerabilities_info,
    
    sm.security_hotspots,
    sm.security_hotspots_high,
    sm.security_hotspots_medium,
    sm.security_hotspots_low,
    
    sm.code_smells,
    sm.comment_lines_density,
    sm.duplicated_lines_density,
    sm.sqale_index,
    sm.sqale_debt_ratio,
    sm.complexity,
    sm.cognitive_complexity,
    
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



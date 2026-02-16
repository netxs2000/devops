-- fct_pm_sonar_quality.sql
-- 逻辑：汇总项目代码质量的最新的状态和趋势
WITH quality AS (
    SELECT * FROM {{ ref('int_sonar_project_quality') }}
)

SELECT
    sonar_project_key,
    sonar_project_name,
    mdm_project_id,
    mdm_product_id,
    last_scan_date,
    coverage,
    bugs,
    vulnerabilities,
    quality_gate_status,
    new_coverage,
    new_bugs,
    increment_quality_status,
    -- 简单等级判断
    CASE 
        WHEN quality_gate_status = 'OK' AND increment_quality_status = 'STABLE' THEN 'EXCELLENT'
        WHEN quality_gate_status = 'OK' AND increment_quality_status = 'RISKY' THEN 'WARNING'
        ELSE 'CRITICAL'
    END AS overall_quality_rating
FROM quality

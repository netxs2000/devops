-- int_sonar_project_quality.sql
-- 逻辑：获取每个 Sonar 项目的最新的质量指标快照并对齐 MDM 资产
WITH projects AS (
    SELECT * FROM {{ ref('stg_sonar_projects') }}
),

latest_measures AS (
    SELECT 
        *,
        ROW_NUMBER() OVER(PARTITION BY project_id ORDER BY analysis_date DESC) as rank
    FROM {{ ref('stg_sonar_measures') }}
),

current_metrics AS (
    SELECT * FROM latest_measures WHERE rank = 1
)

SELECT
    p.sonar_project_key,
    p.sonar_project_name,
    p.mdm_project_id,
    p.mdm_product_id,
    m.analysis_date AS last_scan_date,
    -- 存量健康度
    m.coverage,
    m.bugs,
    m.vulnerabilities,
    m.quality_gate_status,
    -- 增量风险评估
    m.new_coverage,
    m.new_bugs,
    CASE 
        WHEN m.new_bugs > 0 OR m.new_vulnerabilities > 0 THEN 'RISKY'
        WHEN m.quality_gate_status = 'ERROR' THEN 'FAILED'
        ELSE 'STABLE'
    END AS increment_quality_status
FROM projects p
LEFT JOIN current_metrics m ON p.internal_project_id = m.project_id

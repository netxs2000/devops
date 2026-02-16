-- fct_pm_project_health.sql
-- 汇总项目、迭代相关的进度、工时、质量核心指标
WITH project_efforts AS (
    SELECT * FROM {{ ref('int_zentao_execution_efforts') }}
),

execution_details AS (
    SELECT 
        e.execution_id,
        e.execution_name,
        e.execution_type,
        e.execution_status,
        e.start_date,
        e.end_date,
        p.product_name
    FROM {{ ref('stg_zentao_executions') }} e
    LEFT JOIN {{ ref('stg_zentao_products') }} p ON e.product_id = p.product_id
)

SELECT
    d.execution_id,
    d.execution_name,
    d.product_name,
    d.execution_type,
    d.execution_status,
    d.start_date,
    d.end_date,
    f.mdm_project_id,
    -- 核心效能指标
    COALESCE(f.total_task_count, 0) AS task_count,
    COALESCE(f.total_consumed_hours, 0) AS total_effort_hours,
    f.effort_variance,
    -- 计算时间进度 (Time Progress)
    CASE 
        WHEN d.start_date IS NULL OR d.end_date IS NULL THEN 0
        WHEN CURRENT_DATE > d.end_date THEN 1
        WHEN CURRENT_DATE < d.start_date THEN 0
        ELSE ROUND((EXTRACT(EPOCH FROM (CURRENT_DATE - d.start_date)) / EXTRACT(EPOCH FROM (d.end_date - d.start_date)))::numeric, 2)
    END AS time_progress
FROM execution_details d
LEFT JOIN project_efforts f ON d.execution_id = f.execution_id

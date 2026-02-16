-- fct_dora_deployment_frequency.sql
-- 逻辑：按日汇总部署频率，直接支撑 DORA 核心看板
WITH history AS (
    SELECT * FROM {{ ref('int_deployment_history') }}
    WHERE deployment_env = 'prod' -- 仅统计生产环境
)

SELECT
    date_trunc('day', start_time) AS deployment_date,
    mdm_project_id,
    mdm_product_id,
    COUNT(*) AS total_deployments,
    SUM(is_success) AS successful_deployments,
    ROUND(SUM(is_success)::numeric / COUNT(*), 2) AS deployment_success_rate
FROM history
GROUP BY 1, 2, 3
ORDER BY 1 DESC

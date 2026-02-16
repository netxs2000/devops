-- int_deployment_history.sql
-- 逻辑：锁定所有的部署 Job 及其构建历史，用于计算 DORA Metrics
WITH jobs AS (
    SELECT * FROM {{ ref('stg_jenkins_jobs') }}
    WHERE is_deployment = true
),

builds AS (
    SELECT * FROM {{ ref('stg_jenkins_builds') }}
),

deployment_events AS (
    SELECT
        j.job_full_name,
        j.mdm_project_id,
        j.mdm_product_id,
        j.deployment_env,
        b.build_number,
        b.build_result,
        b.start_time,
        b.duration_ms / 1000.0 AS duration_seconds,
        CASE WHEN b.build_result = 'SUCCESS' THEN 1 ELSE 0 END AS is_success
    FROM jobs j
    JOIN builds b ON j.internal_job_id = b.job_id
)

SELECT * FROM deployment_events

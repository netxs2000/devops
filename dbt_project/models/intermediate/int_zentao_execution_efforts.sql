-- int_zentao_execution_efforts.sql
WITH tasks AS (
    -- 提取所有任务及其工时负载
    SELECT 
        issue_unique_id,
        execution_id,
        "left" AS remaining_hours,
        -- 使用 Postgres JSON 操作符提取数值
        (consumed::text)::numeric AS consumed_hours,
        (estimate::text)::numeric AS estimated_hours,
        task_type,
        assigned_to_user_id
    FROM {{ ref('stg_zentao_issues') }}
    WHERE issue_type = 'task'
      AND execution_id IS NOT NULL
),

execution_aggregation AS (
    -- 按执行/迭代层级聚合工时
    SELECT
        execution_id,
        COUNT(issue_unique_id) AS total_task_count,
        SUM(estimated_hours) AS total_estimated_hours,
        SUM(consumed_hours) AS total_consumed_hours,
        -- 计算各类任务的耗时占比 (如开发占 60%，测试占 20%)
        SUM(CASE WHEN task_type = 'devel' THEN consumed_hours ELSE 0 END) AS devel_hours,
        SUM(CASE WHEN task_type = 'test' THEN consumed_hours ELSE 0 END) AS test_hours
    FROM tasks
    GROUP BY 1
),

executions_with_mdm AS (
    -- 关联到 MDM 项目维度
    SELECT 
        e.execution_id,
        e.execution_name,
        e.mdm_project_id,
        a.total_task_count,
        a.total_estimated_hours,
        a.total_consumed_hours,
        a.devel_hours,
        a.test_hours,
        -- 计算偏差率 (预计 vs 实际)
        CASE 
            WHEN a.total_estimated_hours = 0 THEN 0
            ELSE ROUND((a.total_consumed_hours - a.total_estimated_hours) / a.total_estimated_hours, 2)
        END AS effort_variance
    FROM {{ ref('stg_zentao_executions') }} e
    LEFT JOIN execution_aggregation a ON e.execution_id = a.execution_id
)

SELECT * FROM executions_with_mdm

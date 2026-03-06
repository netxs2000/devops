-- stg_zentao_issues.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'zentao_issues') }}
),

renamed AS (
    SELECT
        -- 构造全局唯一 ID：id_type (如 101_task)
        concat(id::text, '_', type) AS issue_unique_id,
        id AS raw_id,
        type AS issue_type,
        product_id,
        execution_id,
        plan_id,
        title AS issue_title,
        status AS issue_status,
        priority,
        estimate,
        consumed,
        NULL::jsonb AS remaining_hours,
        task_type,
        opened_by,
        assigned_to,
        opened_by_user_id,
        assigned_to_user_id,
        created_at,
        updated_at,
        closed_at,
        raw_data
    FROM source
)

SELECT * FROM renamed

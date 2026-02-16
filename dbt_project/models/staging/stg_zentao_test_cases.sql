-- stg_zentao_test_cases.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'zentao_test_cases') }}
),

renamed AS (
    SELECT
        id AS case_id,
        product_id,
        story_id AS requirement_id, -- 对应需求的物理 ID
        title AS case_title,
        type AS case_type,
        status AS case_status,
        last_run_result,
        is_automated,
        automation_type,
        script_path,
        created_at,
        updated_at
    FROM source
)

SELECT * FROM renamed

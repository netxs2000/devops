-- stg_zentao_executions.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'zentao_executions') }}
),

renamed AS (
    SELECT
        id AS execution_id,
        product_id,
        name AS execution_name,
        code AS execution_code,
        type AS execution_type,
        status AS execution_status,
        parent_id,
        path AS execution_path,
        mdm_project_id,
        begin AS start_date,
        "end" AS end_date,
        real_began AS actual_start_date,
        real_end AS actual_end_date,
        created_at,
        updated_at
    FROM source
)

SELECT * FROM renamed

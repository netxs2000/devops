-- stg_zentao_test_results.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'zentao_test_results') }}
),

renamed AS (
    SELECT
        id AS result_id,
        case_id,
        build_id,
        result AS execution_result,
        date AS execution_date,
        last_run_by,
        created_at
    FROM source
)

SELECT * FROM renamed

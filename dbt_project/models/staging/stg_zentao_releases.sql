-- stg_zentao_releases.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'zentao_releases') }}
),

renamed AS (
    SELECT
        id AS release_id,
        product_id,
        build_id,
        plan_id,
        name AS release_name,
        date AS release_date,
        status AS DEPLOYMENT_STATUS,
        opened_by,
        opened_by_user_id,
        raw_data
    FROM source
)

SELECT * FROM renamed

-- stg_zentao_products.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'zentao_products') }}
),

renamed AS (
    SELECT
        id AS product_id,
        name AS product_name,
        code AS product_code,
        status AS product_status,
        mdm_product_id,
        gitlab_project_id,
        created_at,
        updated_at
    FROM source
)

SELECT * FROM renamed

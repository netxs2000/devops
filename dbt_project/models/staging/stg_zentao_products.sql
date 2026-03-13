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
        case 
            when mdm_product_id is not null and mdm_product_id not like 'PROJ-%' 
                then 'PROJ-' || mdm_product_id
            else mdm_product_id
        end as mdm_product_id,
        gitlab_project_id,
        created_at,
        updated_at
    FROM source
)

SELECT * FROM renamed

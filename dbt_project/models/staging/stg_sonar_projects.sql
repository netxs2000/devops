-- stg_sonar_projects.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'sonar_projects') }}
),

renamed AS (
    SELECT
        id AS internal_project_id,
        key AS sonar_project_key,
        name AS sonar_project_name,
        qualifier,
        mdm_project_id,
        mdm_product_id,
        last_analysis_date,
        created_at,
        updated_at
    FROM source
)

SELECT * FROM renamed

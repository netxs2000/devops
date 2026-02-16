-- stg_jenkins_jobs.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'jenkins_jobs') }}
),

renamed AS (
    SELECT
        id AS internal_job_id,
        full_name AS job_full_name,
        name AS job_short_name,
        mdm_project_id,
        mdm_product_id,
        is_deployment,
        deployment_env,
        created_at,
        updated_at
    FROM source
)

SELECT * FROM renamed

-- stg_jenkins_builds.sql
WITH source AS (
    SELECT * FROM {{ source('raw', 'jenkins_builds') }}
),

renamed AS (
    SELECT
        id AS build_internal_id,
        job_id,
        number AS build_number,
        result AS build_result,
        duration AS duration_ms,
        timestamp AS start_time,
        trigger_type,
        trigger_user_id,
        commit_sha,
        created_at
    FROM source
)

SELECT * FROM renamed

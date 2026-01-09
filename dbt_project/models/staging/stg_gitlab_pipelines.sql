
with source as (
    select * from {{ source('raw', 'gitlab_pipelines') }}
),

renamed as (
    select
        id as pipeline_id,
        project_id,
        status,
        ref,
        sha,
        created_at,
        updated_at,
        duration
        -- started_at and finished_at are missing in DB schema
    from source
)

select * from renamed

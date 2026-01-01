
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
        duration,
        started_at,
        finished_at
    from source
)

select * from renamed

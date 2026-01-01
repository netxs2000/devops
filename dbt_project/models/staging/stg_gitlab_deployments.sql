
with source as (
    select * from {{ source('raw', 'gitlab_deployments') }}
),

renamed as (
    select
        id as deployment_id,
        project_id,
        iid,
        ref,
        sha,
        environment,
        status,
        created_at,
        updated_at,
        finished_at
    from source
)

select * from renamed

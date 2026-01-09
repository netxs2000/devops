with source as (
    select * from "devops_db"."public"."gitlab_deployments"
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
        updated_at
        -- finished_at is missing in DB schema
    from source
)

select * from renamed
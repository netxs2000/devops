with source as (
    select * from "devops_db"."public"."gitlab_projects"
),

renamed as (
    select
        id as gitlab_project_id,
        name as project_name,
        path_with_namespace,
        description,
        created_at,
        last_activity_at
        -- visibility and archived are missing in DB schema
    from source
)

select * from renamed
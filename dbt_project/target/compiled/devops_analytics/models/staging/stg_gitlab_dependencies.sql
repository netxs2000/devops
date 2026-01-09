with source as (
    select * from "devops_db"."public"."gitlab_dependencies"
),

renamed as (
    select
        project_id,
        name as dependency_name,
        version,
        package_manager,
        dependency_type
    from source
)

select * from renamed
with source as (
    select * from "devops_db"."public"."gitlab_packages"
),

renamed as (
    select
        id as package_id,
        project_id,
        name as package_name,
        package_type,
        version
    from source
)

select * from renamed
with source as (
    select * from "devops_db"."public"."sonar_projects"
),

renamed as (
    select
        id as sonar_project_id,
        gitlab_project_id,
        name as sonar_project_name,
        key as sonar_project_key
    from source
)

select * from renamed
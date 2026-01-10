
  create view "devops_db"."public_staging"."stg_gitlab_projects__dbt_tmp"
    
    
  as (
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
        last_activity_at,
        coalesce((raw_data->>'archived')::boolean, false) as is_archived
    from source
)

select * from renamed
  );
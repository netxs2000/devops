
  create view "devops_db"."public_staging"."stg_gitlab_dependencies__dbt_tmp"
    
    
  as (
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
  );
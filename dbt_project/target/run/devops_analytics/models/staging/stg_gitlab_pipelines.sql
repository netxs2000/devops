
  create view "devops_db"."public_staging"."stg_gitlab_pipelines__dbt_tmp"
    
    
  as (
    with source as (
    select * from "devops_db"."public"."gitlab_pipelines"
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
  );
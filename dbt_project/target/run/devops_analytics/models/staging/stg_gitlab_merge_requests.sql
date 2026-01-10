
  create view "devops_db"."public_staging"."stg_gitlab_merge_requests__dbt_tmp"
    
    
  as (
    with source as (
    select * from "devops_db"."public"."gitlab_merge_requests"
),

renamed as (
    select
        id as merge_request_id,
        project_id,
        iid,
        title,
        state,
        author_id as author_user_id,
        merged_at,
        created_at,
        merge_commit_sha
        -- labels is missing in DB schema
    from source
)

select * from renamed
  );
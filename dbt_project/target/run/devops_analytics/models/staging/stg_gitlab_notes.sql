
  create view "devops_db"."public_staging"."stg_gitlab_notes__dbt_tmp"
    
    
  as (
    with source as (
    select * from "devops_db"."public"."gitlab_notes"
),

renamed as (
    select
        id as note_id,
        project_id,
        noteable_iid, -- DB has noteable_iid instead of noteable_id
        noteable_type,  -- 'Issue' or 'MergeRequest'
        body,
        author_id as author_user_id,
        created_at,
        system as is_system_note
    from source
    where system = false -- We only care about human interactions for talent analysis
)

select * from renamed
  );
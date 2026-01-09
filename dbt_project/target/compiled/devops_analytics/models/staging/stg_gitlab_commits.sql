with source as (
    select * from "devops_db"."public"."gitlab_commits"
),

renamed as (
    select
        id as commit_sha,
        project_id,
        short_id,
        title,
        author_email,
        committed_date,
        message
    from source
)

select * from renamed
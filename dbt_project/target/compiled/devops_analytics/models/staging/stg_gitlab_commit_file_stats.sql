with source as (
    select * from "devops_db"."public"."gitlab_commit_file_stats"
)

select
    id as file_stat_id,
    commit_id,
    file_path,
    language,
    file_type_category,
    coalesce(code_added, 0) as code_added,
    coalesce(code_deleted, 0) as code_deleted,
    coalesce(comment_added, 0) as comment_added,
    coalesce(comment_deleted, 0) as comment_deleted
from source
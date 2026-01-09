with source as (
    select * from "devops_db"."public"."gitlab_issues"
),

renamed as (
    select
        id as issue_id,
        project_id,
        iid,
        title,
        state,
        author_id as author_user_id,
        created_at,
        closed_at,
        updated_at,
        time_estimate,
        total_time_spent,
        weight,
        work_item_type
    from source
)

select * from renamed
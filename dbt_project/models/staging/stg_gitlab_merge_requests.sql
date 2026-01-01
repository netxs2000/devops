
with source as (
    select * from {{ source('raw', 'gitlab_merge_requests') }}
),

renamed as (
    select
        id as merge_request_id,
        project_id,
        iid,
        title,
        state,
        author_user_id,
        merged_by_user_id,
        merged_at,
        created_at,
        -- Extract Labels from JSONB if needed, keeping it simple for now
        labels
    from source
)

select * from renamed

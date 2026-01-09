
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
        author_id as author_user_id,
        merged_at,
        created_at
        -- labels is missing in DB schema
    from source
)

select * from renamed

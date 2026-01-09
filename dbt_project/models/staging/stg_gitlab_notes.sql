
with source as (
    select * from {{ source('raw', 'gitlab_notes') }}
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

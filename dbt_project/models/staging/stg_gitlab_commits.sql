
with source as (
    select * from {{ source('raw', 'gitlab_commits') }}
),

renamed as (
    select
        id as commit_sha,
        project_id,
        short_id,
        title,
        author_email,
        committed_date,
        message,
        -- 使用正则提取 #123 格式的禅道 ID
        substring(message from '#([0-9]+)') as zentao_id
    from source
)

select * from renamed

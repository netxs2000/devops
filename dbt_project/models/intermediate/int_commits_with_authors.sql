
with commits as (
    select * from {{ ref('stg_gitlab_commits') }}
),

identities as (
    select * from {{ ref('stg_mdm_identities') }}
),

-- 核心逻辑：将物理的 Commit 关联到逻辑的 Person (OneID)
joined as (
    select
        c.commit_sha,
        c.project_id,
        c.committed_date,
        -- 使用 Email 进行关联，这是最常用的软连接方式
        coalesce(i.user_id, '00000000-0000-0000-0000-000000000000'::uuid) as author_user_id,
        c.author_email
    from commits c
    left join identities i on c.author_email = i.email
)

select * from joined

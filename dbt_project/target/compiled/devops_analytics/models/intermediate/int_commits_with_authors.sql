with commits as (
    select * from "devops_db"."public_staging"."stg_gitlab_commits"
),

identities as (
    select * from "devops_db"."public_intermediate"."int_identity_alignment"
),

-- 核心逻辑：使用优先级对齐策略关联 Person (OneID)
joined as (
    select
        c.commit_sha,
        c.project_id,
        c.committed_date,
        c.title,
        -- 通过校准引擎匹配 UserID
        -- 逻辑：优先匹配特定系统的映射，否则回退到通用 Email 匹配
        coalesce(
            (select master_user_id from identities i 
             where i.identifier_type = 'EMAIL' 
               and i.identifier_value = c.author_email 
               and (i.source_system = 'GITLAB' or i.source_system = 'ANY')
             order by priority asc limit 1),
            '00000000-0000-0000-0000-000000000000'::uuid
        ) as author_user_id,
        c.author_email
    from commits c
)

select * from joined
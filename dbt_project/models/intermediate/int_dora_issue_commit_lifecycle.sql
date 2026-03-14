-- 禅道需求与代码提交关联中间表
-- 小白版逻辑：通过代码提交信息里的 #123 找到对应的禅道单子，并计算工作耗时。

with issues as (
    select * from {{ ref('stg_zentao_issues') }}
),

commits as (
    select * from {{ ref('stg_gitlab_commits') }}
    where zentao_id is not null
),

-- 关联
joined as (
    select
        i.issue_unique_id,
        i.raw_id as zentao_issue_id,
        i.issue_type,
        i.product_id,
        i.created_at as issue_created_at,
        c.commit_sha,
        c.project_id as gitlab_project_id,
        c.committed_date,
        c.author_email
    from issues i
    inner join commits c on i.raw_id::text = c.zentao_id
),

-- 聚合每个 Issue 的开发时间线
issue_lifecycle as (
    select
        issue_unique_id,
        zentao_issue_id,
        issue_type,
        product_id,
        issue_created_at,
        min(committed_date) as first_commit_at,
        max(committed_date) as last_commit_at,
        count(distinct commit_sha) as total_commits,
        
        -- 计算从需求创建到开始写代码的“响应延迟”
        extract(epoch from (min(committed_date) - issue_created_at)) / 3600.0 as response_lead_hours,
        
        -- 计算从第一行代码到最后一行代码的“开发时长”
        extract(epoch from (max(committed_date) - min(committed_date))) / 3600.0 as dev_duration_hours
    from joined
    group by 1, 2, 3, 4, 5
)

select * from issue_lifecycle

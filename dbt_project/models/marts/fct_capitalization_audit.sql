
/*
    财务审计：研发投入资本化核算 (Capitalization Audit)
    
    逻辑：
    1. 找到所有标记为 CapEx 的 Epic。
    2. 通过标签关联，找到属于这些 Epic 的 Issues。
    3. 穿透关联：Issue -> Merge Request -> Commits。
    4. 汇总每个 Epic 的代码贡献量，作为资本化比例的审计依据。
*/

with 
epics as (
    select * from {{ ref('stg_mdm_epics') }}
    where is_capitalizable = true
),

issues as (
    select 
        id as issue_id,
        project_id,
        iid as issue_iid,
        labels as issue_labels
    from {{ source('raw', 'gitlab_issues') }}
),

-- 核心黑科技：跨工具“软连接” (Lineage Reconstruction)
-- 假设 Issue 标签中包含 Epic 的 Portfolio Link (如 PORT-2025-Q1)
epic_to_issue as (
    select 
        e.epic_id,
        e.portfolio_link,
        i.issue_id,
        i.project_id
    from epics e
    join issues i on i.issue_labels::text ilike '%' || e.portfolio_link || '%'
),

-- 关联到物理提交
mr_to_issue as (
    select 
        mr.merge_request_id,
        mr.project_id,
        -- 从 MR 的 external_issue_id 关联到 Issue IID
        e2i.issue_id,
        e2i.epic_id
    from {{ ref('stg_gitlab_merge_requests') }} mr
    join epic_to_issue e2i 
        on mr.external_issue_id = e2i.issue_iid::text 
        and mr.project_id = e2i.project_id
),

final_efforts as (
    select
        m2i.epic_id,
        count(distinct c.commit_sha) as total_commits,
        count(distinct c.author_user_id) as contributor_count
    from mr_to_issue m2i
    join {{ ref('int_commits_with_authors') }} c 
        on c.project_id = m2i.project_id
    group by 1
)

select 
    e.epic_id,
    e.epic_title,
    e.portfolio_link,
    coalesce(f.total_commits, 0) as audit_effort_unit, -- 审计单位：提交数
    coalesce(f.contributor_count, 0) as audit_headcount,  -- 投入人数
    -- 计算资本化强度（演示逻辑）
    case 
        when f.total_commits > 100 then 'High Confidence'
        when f.total_commits > 0 then 'Auditable'
        else 'Insufficient Evidence'
    end as audit_status
from epics e
left join final_efforts f on e.epic_id = f.epic_id

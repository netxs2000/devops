
/*
    交付成本度量衡 (The FinOps Bridge / Cost-to-Value)
    
    逻辑：
    1. 整合审计模型中的用户投入。
    2. 关联资源成本表中的单价。
    3. 核算每个战略 Epic 消耗的估算财务金额。
*/

with 
-- 获取用户对 Epic 的投入占比（这里简化为基于 Commit 的分步投入）
user_epic_efforts as (
    select
        m2i.epic_id,
        c.author_user_id as user_id,
        count(distinct c.commit_sha) as commit_count
    from {{ ref('stg_gitlab_merge_requests') }} mr
    join {{ ref('stg_gitlab_commits') }} c on mr.project_id = c.project_id -- 简化逻辑
    join {{ ref('stg_mdm_epics') }} e on mr.external_issue_id::text ilike '%' || e.portfolio_link || '%' -- 软连接
    group by 1, 2
),

-- 获取资源成本
costs as (
    select * from {{ ref('stg_mdm_resource_costs') }}
),

-- 合并成本
calculated_costs as (
    select
        uee.epic_id,
        uee.user_id,
        uee.commit_count,
        coalesce(rc.hourly_rate, 100.0) as rate, -- 默认单价
        -- 这里假设一个 Commit 平均代表 4 小时工作量 (演示逻辑)
        (uee.commit_count * 4 * coalesce(rc.hourly_rate, 100.0)) as estimated_cost
    from user_epic_efforts uee
    left join costs rc on uee.user_id = rc.user_id
)

-- 最终汇聚到 Epic 级别
select
    e.epic_id,
    e.epic_title,
    e.portfolio_link,
    sum(cc.commit_count) as total_commits,
    sum(cc.estimated_cost) as total_accrued_cost,
    current_date as calculated_at
from {{ ref('stg_mdm_epics') }} e
join calculated_costs cc on e.epic_id = cc.epic_id
group by 1, 2, 3

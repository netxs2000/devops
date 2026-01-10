
/*
    交付成本度量衡 (The FinOps Bridge / Cost-to-Value) - Refactored v2
    
    逻辑：
    1. 整合重构后的 DWS 层项目周成本。
    2. 计算每个项目的“单个 MR 成本”及“单位产出价值”。
*/

with 

project_costs as (
    select
        project_id,
        sum(total_human_cost) as total_accrued_cost,
        sum(contributor_count) as total_contributors -- 简化汇总
    from {{ ref('dws_project_costs_weekly') }}
    group by 1
),

project_output as (
    -- 从交付 DWS 获取产出
    select
        project_id,
        sum(mrs_merged) as total_mrs,
        sum(prod_deploys) as total_deploys
    from {{ ref('dws_project_metrics_daily') }}
    group by 1
),

projects as (
    select * from {{ ref('stg_gitlab_projects') }}
)

select
    p.gitlab_project_id,
    p.project_name,
    coalesce(pc.total_accrued_cost, 0) as total_cost,
    
    -- 效率指标
    case 
        when coalesce(po.total_mrs, 0) > 0 
        then round((pc.total_accrued_cost / po.total_mrs)::numeric, 2)
        else null 
    end as cost_per_mr,
    
    coalesce(po.total_deploys, 0) as prod_deploys,
    
    -- 成本效益等级
    case 
        when (pc.total_accrued_cost / nullif(po.total_mrs, 0)) < 500 then 'High Efficiency'
        when (pc.total_accrued_cost / nullif(po.total_mrs, 0)) > 2000 then 'Heavy Investment'
        else 'Optimal'
    end as efficiency_rating

from projects p
left join project_costs pc on cast(p.gitlab_project_id as varchar) = pc.project_id
left join project_output po on p.gitlab_project_id = po.project_id
where p.is_archived = false


/*
    DWS: 项目每周成本汇总 (Project Weekly Cost Summary)
    
    汇总单个项目在每周的人力投入成本。
    事实表粒度：项目 + 统计周
*/

with 

daily_costs as (
    select * from {{ ref('int_developer_daily_costs') }}
),

project_weekly as (
    select
        project_id,
        date_trunc('week', metric_date)::date as metric_week,
        count(distinct user_id) as contributor_count,
        sum(daily_cost_amount) as total_human_cost,
        currency
    from daily_costs
    group by 1, 2, 5
)

select
    project_id,
    metric_week,
    contributor_count,
    total_human_cost,
    currency,
    
    -- 累计成本 (Window Function)
    sum(total_human_cost) over (partition by project_id order by metric_week) as running_total_cost

from project_weekly

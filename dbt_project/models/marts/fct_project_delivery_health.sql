
/*
    项目交付健康度全景 (Project Delivery Health 360) - Refactored v2
    
    该模型是交付体系的“上帝视角”，整合了来自 DWS 层的聚合指标。
    大幅简化了关联逻辑，提高了查询响应速度。
*/

with 

projects as (
    select * from {{ ref('stg_gitlab_projects') }}
),

-- 从 DWS 层获取汇总指标 (按项目聚合所有日期的总和)
dws_project_summary as (
    select
        project_id,
        sum(mrs_merged) as merged_mr_total,
        count(*) filter (where mrs_opened > 0) as active_days_count,
        sum(prod_deploys) as total_prod_deploys,
        -- 质量指标取最新一天的记录 (或均值)
        max(sonar_bugs) as latest_bug_count,
        max(test_coverage_pct) as latest_coverage,
        max(tech_debt_minutes) as latest_tech_debt
    from {{ ref('dws_project_metrics_daily') }}
    group by 1
),

-- 补充未闭环的活跃 MR 排队情况 (实时性要求较高，可保持从 Staging 取)
mr_backlog as (
    select
        project_id,
        count(*) as open_mr_count
    from {{ ref('stg_gitlab_merge_requests') }}
    where state = 'opened'
    group by 1
)

select
    p.gitlab_project_id,
    p.project_name,
    p.path_with_namespace,
    
    -- 质量指标
    coalesce(s.latest_bug_count, 0) as bug_count,
    coalesce(s.latest_coverage, 0) as test_coverage_pct,
    round(coalesce(s.latest_tech_debt, 0) / 60.0, 1) as tech_debt_hours,
    
    -- 产出指标
    coalesce(s.merged_mr_total, 0) as merged_mr_total,
    coalesce(b.open_mr_count, 0) as mr_backlog,
    coalesce(s.total_prod_deploys, 0) as prod_deploys,
    
    -- 综合健康分计算 (逻辑同 v1)
    round(
        100 
        - (least(coalesce(s.latest_bug_count, 0) * 2, 20))
        - (case when coalesce(s.latest_coverage, 0) < 50 then (50 - s.latest_coverage) else 0 end)
        + (least(coalesce(s.total_prod_deploys, 0) * 5, 20))
    ) as health_score
    
from projects p
left join dws_project_summary s on p.gitlab_project_id = s.project_id
left join mr_backlog b on p.gitlab_project_id = b.project_id
where p.is_archived = false
order by health_score desc

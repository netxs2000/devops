/*
    DORA 精细化度量模型 (Refined DORA Metrics)
    
    逻辑：集成瓶颈分析，提供更具深度的 DORA 指标报告。
*/

with 
bottlenecks as (
    select * from "devops_db"."public_marts"."dws_delivery_bottleneck_analysis"
),

deployments as (
    select 
        project_id,
        date_trunc('month', created_at) as month,
        count(*) as deploy_count,
        sum(case when status != 'success' then 1 else 0 end) as failed_deploys
    from "devops_db"."public_staging"."stg_gitlab_deployments"
    where environment = 'production'
    group by 1, 2
),

projects as (
    select * from "devops_db"."public_staging"."stg_gitlab_projects"
)

select
    p.project_name,
    b.audit_month as month,
    
    -- DORA Core 4
    coalesce(d.deploy_count, 0) as deployment_frequency,
    b.avg_cycle_time_hours as lead_time_hours,
    round((coalesce(d.failed_deploys, 0)::numeric / nullif(d.deploy_count, 0) * 100), 2) as change_failure_rate_pct,
    
    -- 精细化分析维度
    b.avg_pickup_delay_hours as wait_time_hours,
    b.avg_review_duration_hours as work_time_hours,
    b.primary_bottleneck,
    
    -- 效能评级
    case 
        when b.avg_cycle_time_hours < 24 then 'ELITE'
        when b.avg_cycle_time_hours < 72 then 'HIGH'
        when b.avg_cycle_time_hours < 168 then 'MEDIUM'
        else 'LOW'
    end as performance_rating

from bottlenecks b
left join deployments d on b.project_id = d.project_id and b.audit_month = d.month
left join projects p on b.project_id = p.gitlab_project_id
order by month desc, lead_time_hours asc
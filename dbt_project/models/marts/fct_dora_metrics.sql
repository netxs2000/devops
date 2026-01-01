
/*
    DORA 指标核心模型 (DORA Metrics Mart)
    
    逻辑：
    1. Deployment Frequency: 生产环境部署次数。
    2. Lead Time for Changes: 从代码合并到发布的时间。
    3. Change Failure Rate: 部署失败比率。
    4. MTTR: 故障恢复时间（通过 Issue 标签识别 Incident）。
*/

with 

-- 1. 发布频率 (Deployment Frequency)
deployments as (
    select 
        project_id,
        date_trunc('month', created_at) as month,
        count(*) as deploy_count,
        sum(case when status != 'success' then 1 else 0 end) as failed_deploys
    from {{ ref('stg_gitlab_deployments') }}
    where environment = 'production'
    group by 1, 2
),

-- 2. 变更前置时间 (Lead Time for Changes)
lead_times as (
    select
        project_id,
        date_trunc('month', merged_at) as month,
        avg(extract(epoch from (merged_at - created_at))/60.0) as avg_lead_time_minutes
    from {{ ref('stg_gitlab_merge_requests') }}
    where state = 'merged'
    group by 1, 2
),

-- 3. MTTR (基于 Issue 识别 Incident)
mttr as (
    select
        project_id,
        date_trunc('month', closed_at) as month,
        avg(extract(epoch from (closed_at - created_at))/3600.0) as avg_recovery_time_hours
    from {{ ref('stg_gitlab_issues') }}
    where state = 'closed'
      and labels::text ilike '%incident%' -- 简单识别逻辑
    group by 1, 2
)

select
    p.project_name,
    d.month,
    coalesce(d.deploy_count, 0) as deployment_frequency,
    round(coalesce(lt.avg_lead_time_minutes, 0)::numeric, 1) as lead_time_minutes,
    round((coalesce(d.failed_deploys, 0)::numeric / nullif(d.deploy_count, 0) * 100), 2) as change_failure_rate_pct,
    round(coalesce(m.avg_recovery_time_hours, 0)::numeric, 1) as mttr_hours
from {{ ref('stg_gitlab_projects') }} p
join deployments d on p.gitlab_project_id = d.project_id
left join lead_times lt on p.gitlab_project_id = lt.project_id and d.month = lt.month
left join mttr m on p.gitlab_project_id = m.project_id and d.month = m.month
order by d.month desc, p.project_name

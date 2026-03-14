
/*
    DORA 精细化度量模型 (Refined DORA Metrics)
    
    逻辑：集成瓶颈分析，提供更具深度的 DORA 指标报告。
*/

with 
bottlenecks as (
    select * from {{ ref('dws_delivery_bottleneck_analysis') }}
),

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

-- 提取 ZenTao 中类型为 Bug 的事故恢复时间 (从创建到关闭的小时数)
incidents as (
    select
        rm.master_project_id,
        date_trunc('month', i.created_at) as month,
        extract(epoch from (i.closed_at - i.created_at))/3600.0 as restore_hours
    from {{ ref('stg_zentao_issues') }} i
    join {{ ref('int_project_resource_map') }} rm 
        on (i.execution_id::text = rm.external_resource_id or i.product_id::text = rm.external_resource_id)
        and rm.system_code = 'zentao-prod'
    where i.issue_type = 'bug' and i.closed_at is not null
),

-- 通过 master_project_id 将 MTTR 映射回对应的 GitLab 项目级维度
mttr_by_gitlab as (
    select 
        gl_rm.external_resource_id::int as gitlab_project_id,
        i.month,
        avg(i.restore_hours) as avg_restore_hours
    from incidents i
    join {{ ref('int_project_resource_map') }} gl_rm 
        on i.master_project_id = gl_rm.master_project_id and gl_rm.system_code = 'gitlab-prod'
    group by 1, 2
),

projects as (
    select * from {{ ref('stg_gitlab_projects') }}
),

nexus_metrics as (
    select
        gitlab_project_id,
        date_trunc('month', nexus_created_at) as month,
        avg(build_latency_minutes) as avg_build_latency_minutes
    from {{ ref('int_nexus_commits') }}
    group by 1, 2
)

select
    p.project_name,
    b.audit_month as month,
    
    -- DORA Core 4
    coalesce(d.deploy_count, 0) as deployment_frequency,
    round(coalesce(mttr.avg_restore_hours, 0)::numeric, 2) as mtr_hours,
    b.avg_cycle_time_hours as lead_time_hours,
    round((coalesce(d.failed_deploys, 0)::numeric / nullif(d.deploy_count, 0) * 100), 2) as change_failure_rate_pct,
    
    -- 精细化分析维度
    b.avg_pickup_delay_hours as wait_time_hours,
    b.avg_review_duration_hours as work_time_hours,
    round(coalesce(n.avg_build_latency_minutes, 0)::numeric, 2) as build_latency_minutes, -- 新增：从代码提交到打包完成的耗时
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
left join mttr_by_gitlab mttr on b.project_id = mttr.gitlab_project_id and b.audit_month = mttr.month
left join projects p on b.project_id = p.gitlab_project_id
left join nexus_metrics n on b.project_id = n.gitlab_project_id and b.audit_month = n.month
order by month desc, lead_time_hours asc

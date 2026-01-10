
/*
    DWS: 项目每日指标汇总 (Project Daily Metrics Summary) - Refactored v2
    
    汇总单个项目在每一天的交付、质量和活跃度指标。
    本层作为汇总视图，直接引用专门的交付、质量相关 DWS 模型。
*/

with 

calendar as (
    select distinct date_trunc('day', occurred_at)::date as metric_date
    from {{ ref('int_unified_activities') }}
),

projects as (
    select gitlab_project_id as project_id from {{ ref('stg_gitlab_projects') }}
),

project_calendar as (
    select p.project_id, c.metric_date
    from projects p
    cross join calendar c
),

-- 1. 交付活跃度 (基于 MR)
mr_stats as (
    select
        project_id,
        date_trunc('day', created_at)::date as metric_date,
        count(*) as mrs_opened_count,
        count(*) filter (where state = 'merged') as mrs_merged_count
    from {{ ref('stg_gitlab_merge_requests') }}
    group by 1, 2
),

-- 2. 部署活跃度
deploy_stats as (
    select
        project_id,
        date_trunc('day', created_at)::date as metric_date,
        count(*) filter (where environment = 'production' and status = 'success') as successful_prod_deploys,
        count(*) filter (where status = 'failed') as failed_deployments
    from {{ ref('stg_gitlab_deployments') }}
    group by 1, 2
),

-- 3. 质量数据 (直接引用新构建的质量 DWS)
sonar_stats as (
    select
        gitlab_project_id as project_id,
        analysis_day as metric_date,
        bugs as bug_count,
        vulnerabilities as vulnerability_count,
        coverage as avg_test_coverage,
        tech_debt_hours as tech_debt_hours,
        quality_gate_status
    from {{ ref('dws_project_quality_daily') }}
)

select
    pc.project_id,
    pc.metric_date,
    
    -- 交付
    coalesce(ms.mrs_opened_count, 0) as mrs_opened,
    coalesce(ms.mrs_merged_count, 0) as mrs_merged,
    coalesce(ds.successful_prod_deploys, 0) as prod_deploys,
    coalesce(ds.failed_deployments, 0) as failed_deploys,
    
    -- 质量 (单位对齐：统一使用小时作为技术债单位)
    coalesce(ss.bug_count, 0) as sonar_bugs,
    coalesce(ss.vulnerability_count, 0) as sonar_vulnerabilities,
    coalesce(ss.avg_test_coverage, 0) as test_coverage_pct,
    coalesce(ss.tech_debt_hours, 0) as tech_debt_hours,
    ss.quality_gate_status,
    
    -- 活跃度标记
    (coalesce(ms.mrs_opened_count, 0) + coalesce(ds.successful_prod_deploys, 0) > 0) as is_active_day

from project_calendar pc
left join mr_stats ms on pc.project_id = ms.project_id and pc.metric_date = ms.metric_date
left join deploy_stats ds on pc.project_id = ds.project_id and pc.metric_date = ds.metric_date
left join sonar_stats ss on pc.project_id = ss.project_id and pc.metric_date = ss.metric_date
where coalesce(ms.mrs_opened_count, ds.successful_prod_deploys, ss.bug_count, 0) > 0

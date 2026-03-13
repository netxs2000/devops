
{{
    config(
        materialized='incremental',
        unique_key="concat(project_id, '_', metric_date)",
        on_schema_change='append_new_columns'
    )
}}

/*
    DWS: 项目每日指标汇总 (Project Daily Metrics Summary) - Refactored v3 (Incremental)
    
    汇总单个项目在每一天的交付、质量、任务和活跃度指标。
    支持 GitLab (代码/部署/MR) 和 ZenTao (需求/任务/Bug)。
*/

with 

resource_map as (
    select * from {{ ref('int_project_resource_map') }}
),

-- 1. 交付活跃度 (基于 GitLab MR)
mr_stats as (
    select
        rm.master_project_id as project_id,
        date_trunc('day', m.created_at)::date as metric_date,
        count(*) as mrs_opened_count,
        count(*) filter (where m.state = 'merged') as mrs_merged_count
    from {{ ref('stg_gitlab_merge_requests') }} m
    join resource_map rm on m.project_id::text = rm.external_resource_id and rm.system_code = 'gitlab-prod'
    {% if is_incremental() %}
    where m.created_at >= (select max(metric_date) - interval '3 days' from {{ this }})
    {% endif %}
    group by 1, 2
),

-- 2. 部署活跃度 (基于 GitLab Deployments)
deploy_stats as (
    select
        rm.master_project_id as project_id,
        date_trunc('day', d.created_at)::date as metric_date,
        count(*) filter (where d.environment = 'production' and d.status = 'success') as successful_prod_deploys,
        count(*) filter (where d.status = 'failed') as failed_deployments
    from {{ ref('stg_gitlab_deployments') }} d
    join resource_map rm on d.project_id::text = rm.external_resource_id and rm.system_code = 'gitlab-prod'
    {% if is_incremental() %}
    where d.created_at >= (select max(metric_date) - interval '3 days' from {{ this }})
    {% endif %}
    group by 1, 2
),

-- 3. 任务与缺陷活跃度 (基于 ZenTao)
zentao_stats as (
    select
        rm.master_project_id as project_id,
        date_trunc('day', i.created_at)::date as metric_date,
        count(*) filter (where i.issue_type = 'story') as stories_opened,
        count(*) filter (where i.issue_type = 'bug') as bugs_opened,
        count(*) filter (where i.issue_type = 'task') as tasks_opened,
        count(*) filter (where i.issue_status in ('closed', 'finished', 'resolved')) as items_closed
    from {{ ref('stg_zentao_issues') }} i
    join resource_map rm on (i.execution_id::text = rm.external_resource_id or i.product_id::text = rm.external_resource_id)
        and rm.system_code = 'zentao-prod'
    {% if is_incremental() %}
    where i.created_at >= (select max(metric_date) - interval '3 days' from {{ this }})
    {% endif %}
    group by 1, 2
),

-- 4. 质量数据 (引用已增量物化的质量 DWS)
sonar_stats as (
    select
        master_entity_id as project_id,
        analysis_day as metric_date,
        bugs as bug_count,
        vulnerabilities as vulnerability_count,
        coverage as avg_test_coverage,
        tech_debt_hours as tech_debt_hours,
        quality_gate_status
    from {{ ref('dws_project_quality_daily') }}
    {% if is_incremental() %}
    where analysis_day >= (select max(metric_date) - interval '3 days' from {{ this }})
    {% endif %}
),

-- 5. 最终汇聚
all_dates_projects as (
    select distinct project_id, metric_date from mr_stats
    union
    select distinct project_id, metric_date from deploy_stats
    union
    select distinct project_id, metric_date from zentao_stats
    union
    select distinct project_id, metric_date from sonar_stats
)

select
    adp.project_id,
    adp.metric_date,
    
    -- GitLab 交付
    coalesce(ms.mrs_opened_count, 0) as mrs_opened,
    coalesce(ms.mrs_merged_count, 0) as mrs_merged,
    coalesce(ds.successful_prod_deploys, 0) as prod_deploys,
    coalesce(ds.failed_deployments, 0) as failed_deploys,
    
    -- ZenTao 任务/Bug
    coalesce(zs.stories_opened, 0) as zentao_stories_opened,
    coalesce(zs.bugs_opened, 0) as zentao_bugs_opened,
    coalesce(zs.tasks_opened, 0) as zentao_tasks_opened,
    coalesce(zs.items_closed, 0) as zentao_items_closed,

    -- Sonar 质量
    coalesce(ss.bug_count, 0) as sonar_bugs,
    coalesce(ss.vulnerability_count, 0) as sonar_vulnerabilities,
    coalesce(ss.avg_test_coverage, 0) as test_coverage_pct,
    coalesce(ss.tech_debt_hours, 0) as tech_debt_hours,
    ss.quality_gate_status,
    
    -- 活跃度标记
    (
        coalesce(ms.mrs_opened_count, 0) + 
        coalesce(ds.successful_prod_deploys, 0) + 
        coalesce(zs.tasks_opened, 0) +
        coalesce(zs.items_closed, 0) > 0
    ) as is_active_day

from all_dates_projects adp
left join mr_stats ms on adp.project_id = ms.project_id and adp.metric_date = ms.metric_date
left join deploy_stats ds on adp.project_id = ds.project_id and adp.metric_date = ds.metric_date
left join zentao_stats zs on adp.project_id = zs.project_id and adp.metric_date = zs.metric_date
left join sonar_stats ss on adp.project_id = ss.project_id and adp.metric_date = ss.metric_date

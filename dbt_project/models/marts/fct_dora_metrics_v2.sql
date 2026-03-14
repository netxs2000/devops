-- DORA 2.0 核心指标模型 (基于禅道发布记录与生产事故规则)
-- 小白版逻辑：集成最真实的上报数据，滤除开发过程噪音。

with 
-- 1. 部署记录 (以禅道发布为准)
deployments as (
    select
        product_id,
        date_trunc('month', release_date) as month,
        count(release_id) as deployment_frequency
    from {{ ref('stg_zentao_releases') }}
    group by 1, 2
),

-- 2. 生产事故 (P1 & 生产环境)
incidents as (
    select
        product_id,
        date_trunc('month', incident_created_at) as month,
        count(issue_unique_id) as incident_count,
        avg(restore_hours) as mttr_hours
    from {{ ref('int_dora_production_incidents') }}
    group by 1, 2
),

-- 3. 前置时间 (从代码首次提交到发布完成)
-- 这是一个复杂的关联，目前先计算关联到该产品的 Issue 的平均开发周期
lead_time as (
    select
        product_id,
        date_trunc('month', last_commit_at) as month,
        avg(response_lead_hours + dev_duration_hours) as avg_work_hours
    from {{ ref('int_dora_issue_commit_lifecycle') }}
    group by 1, 2
),

-- 基础信息
products as (
    select 
        product_id, 
        product_name,
        gitlab_project_id
    from {{ ref('stg_zentao_products') }}
)

select
    p.product_name,
    coalesce(d.month, i.month, l.month) as audit_month,
    
    -- DORA Core 4
    coalesce(d.deployment_frequency, 0) as deployment_frequency,
    round(coalesce(i.mttr_hours, 0)::numeric, 2) as mttr_hours,
    round(coalesce(l.avg_work_hours, 0)::numeric, 2) as lead_time_hours,
    
    -- 变更失败率 (事故数 / 发布数)
    round(
        (coalesce(i.incident_count, 0)::numeric / nullif(d.deployment_frequency, 0) * 100), 
        2
    ) as change_failure_rate_pct,
    
    -- 识别线上事故数
    coalesce(i.incident_count, 0) as production_incidents_count

from products p
full join deployments d on p.product_id = d.product_id
full join incidents i on p.product_id = i.product_id and d.month = i.month
full join lead_time l on p.product_id = l.product_id and (d.month = l.month or i.month = l.month)
where p.product_id is not null
order by audit_month desc, deployment_frequency desc

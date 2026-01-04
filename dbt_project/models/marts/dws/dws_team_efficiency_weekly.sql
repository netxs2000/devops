
/*
    DWS: 团队周效指标汇总 (Team Weekly Efficiency Summary)
    
    汇总各部门（团队）在周维度的交付效率、吞吐量和工作分布。
    事实表粒度：部门 + 统计周
*/

with 

calendar as (
    -- 生成周时间维度（以周一作为起始）
    select distinct date_trunc('week', metric_date)::date as metric_week
    from {{ ref('dws_developer_metrics_daily') }}
),

departments as (
    select distinct department from {{ ref('stg_mdm_identities') }}
    where department is not null
),

dept_calendar as (
    select d.department, c.metric_week
    from departments d
    cross join calendar c
),

-- 1. 团队规模与基础活跃度 (基于开发者日报)
team_activity as (
    select
        u.department,
        date_trunc('week', d.metric_date)::date as metric_week,
        count(distinct d.user_id) as active_dev_count,
        sum(d.commit_count) as total_commits,
        sum(d.review_count) as total_reviews,
        sum(d.daily_impact_score) as total_impact_score
    from {{ ref('dws_developer_metrics_daily') }} d
    join {{ ref('stg_mdm_identities') }} u on d.user_id = u.user_id
    group by 1, 2
),

-- 2. 交付吞吐量与前导时间 (基于工作项)
work_item_stats as (
    select
        u.department,
        date_trunc('week', w.closed_at)::date as metric_week,
        count(*) as items_completed,
        avg(extract(epoch from (w.closed_at - w.created_at)) / 86400.0) as avg_lead_time_days,
        sum(w.spent_seconds) / 3600.0 as total_spent_hours,
        -- 工作项分布
        count(*) filter (where w.work_item_type in ('Bug', 'Defect')) as bug_fix_count,
        count(*) filter (where w.work_item_type in ('Story', 'Feature', 'Requirement')) as feature_count
    from {{ ref('int_unified_work_items') }} w
    join {{ ref('stg_mdm_identities') }} u on w.author_user_id = u.user_id
    where w.closed_at is not null
    group by 1, 2
)

select
    pc.department,
    pc.metric_week,
    
    -- 资源投入
    coalesce(ta.active_dev_count, 0) as active_dev_count,
    
    -- 产出汇总
    coalesce(ta.total_commits, 0) as total_commits,
    coalesce(ta.total_reviews, 0) as total_reviews,
    coalesce(ta.total_impact_score, 0) as team_impact_score,
    
    -- 交付效率
    coalesce(ws.items_completed, 0) as items_resolved,
    round(coalesce(ws.avg_lead_time_days, 0)::numeric, 2) as avg_lead_time_days,
    round(coalesce(ws.total_spent_hours, 0)::numeric, 1) as total_spent_hours,
    
    -- 吞吐量对比
    coalesce(ws.feature_count, 0) as features_resolved,
    coalesce(ws.bug_fix_count, 0) as bugs_resolved,
    
    -- 派生指标：人均产出
    case 
        when coalesce(ta.active_dev_count, 0) > 0 
        then round((coalesce(ws.items_completed, 0)::numeric / ta.active_dev_count), 2)
        else 0 
    end as velocity_per_dev

from dept_calendar pc
left join team_activity ta on pc.department = ta.department and pc.metric_week = ta.metric_week
left join work_item_stats ws on pc.department = ws.department and pc.metric_week = ws.metric_week
where coalesce(ta.active_dev_count, ws.items_completed, 0) > 0

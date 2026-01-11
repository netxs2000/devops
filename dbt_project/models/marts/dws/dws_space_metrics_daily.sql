
/*
    DWS: SPACE 框架每日指标汇总 (SPACE Framework Daily Metrics)
    
    整合 SPACE 框架的五个维度数据，为开发者个人和团队提供平衡度量。
    事实表粒度：用户 + 日期
*/

with 

-- 1. Activity & Performance & Collaboration (从现有开发者 DWS 获取)
dev_dws as (
    select
        user_id,
        metric_date,
        commit_count,
        review_count,
        daily_impact_score as activity_score,
        mr_merge_count as performance_count
    from {{ ref('dws_developer_metrics_daily') }}
),

-- 2. Satisfaction (满意度 - 来自调查记录)
satisfaction as (
    select
        u.user_id,
        s.date as metric_date,
        avg(s.score) as avg_satisfaction_score
    from {{ source('raw', 'satisfaction_records') }} s
    join {{ ref('stg_mdm_identities') }} u on s.user_email = u.email
    group by 1, 2
),

-- 3. Efficiency (效率 - 暂时用个人的平均工作项闭环时长指代)
efficiency as (
    select
        author_user_id as user_id,
        date_trunc('day', closed_at)::date as metric_date,
        avg(extract(epoch from (closed_at - created_at)) / 3600.0) as avg_lead_time_hours
    from {{ ref('int_unified_work_items') }}
    where closed_at is not null
    group by 1, 2
)

select
    d.user_id,
    d.metric_date,
    
    -- S: Satisfaction
    coalesce(s.avg_satisfaction_score, 0) as s_satisfaction,
    
    -- P: Performance
    coalesce(d.performance_count, 0) as p_performance,
    
    -- A: Activity
    coalesce(d.activity_score, 0) as a_activity,
    
    -- C: Collaboration
    coalesce(d.review_count, 0) as c_collaboration,
    
    -- E: Efficiency
    round(coalesce(e.avg_lead_time_hours, 0)::numeric, 2) as e_efficiency_hours,

    -- Total Score (Average of 5 dimensions)
    round(
        (
            coalesce(s.avg_satisfaction_score, 0) +
            coalesce(d.performance_count, 0) +
            coalesce(d.activity_score, 0) +
            coalesce(d.review_count, 0) +
            round(coalesce(e.avg_lead_time_hours, 0)::numeric, 2)
        ) / 5.0, 
    2) as total_space_score

from dev_dws d
left join satisfaction s on d.user_id = s.user_id and d.metric_date = s.metric_date
left join efficiency e on d.user_id = e.user_id and d.metric_date = e.metric_date

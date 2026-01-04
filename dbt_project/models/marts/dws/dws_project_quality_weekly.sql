
/*
    DWS: 项目每周质量变化汇总 (Project Weekly Quality Aggregation)
    
    逻辑：
    1. 按周汇总质量指标变化趋势。
    2. 计算周平均覆盖率、周内 Bug 净增/净减。
    
    事实表粒度：master_entity_id + metric_week
*/

with 

daily_quality as (
    select * from {{ ref('dws_project_quality_daily') }}
),

weekly_stats as (
    select
        master_entity_id,
        date_trunc('week', analysis_day)::date as metric_week,
        
        -- 期末值 (取本周最后一天的值)
        last_value(bugs) over (partition by master_entity_id, date_trunc('week', analysis_day) order by analysis_day rows between unbounded preceding and unbounded following) as weekly_closing_bugs,
        last_value(tech_debt_hours) over (partition by master_entity_id, date_trunc('week', analysis_day) order by analysis_day rows between unbounded preceding and unbounded following) as weekly_closing_tech_debt,
        
        -- 周内平均值
        avg(coverage) as avg_weekly_coverage,
        
        -- 周内活跃度
        count(*) as scan_days_count,
        sum(daily_bugs_net_change) as total_weekly_bugs_change

    from daily_quality
    group by 1, 2, bugs, tech_debt_hours, analysis_day -- 注意：为了 last_value 窗口函数，group by 需要包含分区外的维度
),

final_weekly as (
    select distinct
        master_entity_id,
        metric_week,
        weekly_closing_bugs,
        weekly_closing_tech_debt,
        avg_weekly_coverage,
        scan_days_count,
        total_weekly_bugs_change
    from weekly_stats
)

select * from final_weekly

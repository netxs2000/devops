/*
    DWS: 项目每日质量快照 (Project Daily Quality Snapshot)
    
    逻辑：
    1. 针对每个项目，取每一天中最后一次（最新）的扫描结果作为该日的质量记录。
    2. 计算核心维度的日环比变化。
    
    事实表粒度：master_entity_id + analysis_day
*/

with 

scans as (
    select * from "devops_db"."public_intermediate"."int_sonar_quality_scans"
),

-- 获取每日最后一次扫描
daily_latest_scans as (
    select
        *,
        row_number() over (partition by master_entity_id, analysis_day order by analysis_date desc) as rank_desc
    from scans
),

filtered_scans as (
    select * from daily_latest_scans where rank_desc = 1
),

-- 计算昨日数据对比 (可选，增加指标洞察)
trend_scans as (
    select
        f.*,
        lag(f.bugs) over (partition by f.master_entity_id order by f.analysis_day) as prev_day_bugs,
        lag(f.tech_debt_hours) over (partition by f.master_entity_id order by f.analysis_day) as prev_day_tech_debt
    from filtered_scans f
)

select
    master_entity_id,
    gitlab_project_id,
    sonar_project_key,
    analysis_day,
    
    quality_gate_status,
    bugs,
    vulnerabilities,
    code_smells,
    coverage,
    tech_debt_hours,
    complexity,
    ncloc,
    
    -- 计算趋势
    (bugs - coalesce(prev_day_bugs, bugs)) as daily_bugs_net_change,
    (tech_debt_hours - coalesce(prev_day_tech_debt, tech_debt_hours)) as daily_tech_debt_net_change

from trend_scans
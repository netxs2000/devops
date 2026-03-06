
/*
    代码质量风险审计事实表 (Quality Risk Audit)
    
    基于 DWS 层质量趋势，自动识别“高风险”资产。
    风险判定标准：
    1. 质量门禁状态为 ERROR。
    2. 单元测试覆盖率 < 30%。
    3. 技术债 > 40 小时。
*/

with 

latest_quality as (
    select
        *,
        row_number() over (partition by master_entity_id order by analysis_day desc) as latest_rank
    from {{ ref('dws_project_quality_daily') }}
),

weekly_trend as (
    select
        master_entity_id,
        total_weekly_bugs_change,
        metric_week
    from {{ ref('dws_project_quality_weekly') }}
    where metric_week = date_trunc('week', current_date)::date -- 仅看本周
),

topology as (
    -- 获取业务系统拓扑资产名称
    select 
        topology_id,
        resource_name,
        master_project_id
    from {{ ref('stg_mdm_entity_topology') }}
)

select
    t.resource_name as project_name,
    q.analysis_day as last_scan_date,
    q.quality_gate_status,
    q.bugs,
    q.coverage,
    q.tech_debt_hours,
    w.total_weekly_bugs_change as bugs_added_this_week,
    
    -- 风险级别判定 (简化逻辑以对齐当前字段)
    case 
        when q.quality_gate_status = 'ERROR' or q.coverage < 30 or q.bugs > 50 then 'CRITICAL'
        when q.coverage < 50 or q.tech_debt_hours > 20 then 'HIGH'
        when q.bugs > 0 then 'MEDIUM'
        else 'LOW'
    end as risk_level,
    
    -- 改进建议
    case
        when q.coverage < 50 then 'Unit tests focus required'
        when q.tech_debt_hours > 40 then 'Refactoring debt reduction'
        when coalesce(w.total_weekly_bugs_change, 0) > 5 then 'Stability drill-down'
        else 'Maintain standards'
    end as recommended_action

from latest_quality q
join topology t on q.master_entity_id = t.topology_id
left join weekly_trend w on q.master_entity_id = w.master_entity_id
where q.latest_rank = 1

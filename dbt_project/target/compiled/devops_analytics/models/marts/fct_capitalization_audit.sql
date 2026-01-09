/*
    研发资本化审计事实模型 (Capitalization Audit Fact)
    
    逻辑：
    1. 聚合各项目在不同时间段的 CapEx vs OpEx 活动分布。
    2. 计算资本化率 (Capitalization Rate)。
    3. 为合规性审计提供明细链路，直到具体的 Commit 或 MR。
*/

with classified_activities as (
    select * from "devops_db"."public_intermediate"."int_activity_financial_classification"
),

weekly_summary as (
    select
        target_entity_id as project_id, -- 简化处理，实际应解析 REPO ID
        date_trunc('week', occurred_at) as audit_week,
        financial_category,
        count(*) as activity_count,
        sum(base_impact_score) as total_impact
    from classified_activities
    where target_entity_type = 'REPO'
    group by 1, 2, 3
),

pivot_summary as (
    select
        project_id,
        audit_week,
        sum(case when financial_category = 'CapEx' then total_impact else 0 end) as capex_impact,
        sum(case when financial_category = 'OpEx' then total_impact else 0 end) as opex_impact,
        sum(total_impact) as total_impact
    from weekly_summary
    group by 1, 2
)

select
    project_id,
    audit_week,
    capex_impact,
    opex_impact,
    total_impact,
    case 
        when total_impact > 0 then round(capex_impact * 100.0 / total_impact, 2)
        else 0 
    end as capitalization_rate,
    
    -- 审计状态
    case 
        when (capex_impact * 100.0 / nullif(total_impact, 0)) > 80 then 'HIGH_CAPEX_INSPECTION_REQUIRED'
        when total_impact > 100 then 'AUDIT_READY'
        else 'INSUFFICIENT_DATA'
    end as audit_status
from pivot_summary
order by audit_week desc, capitalization_rate desc
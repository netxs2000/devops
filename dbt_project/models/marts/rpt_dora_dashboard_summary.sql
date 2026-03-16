-- rpt_dora_dashboard_summary.sql
-- 专为前端大屏优化的预聚合模型 (Pre-aggregated DORA Summary)
-- 包含最新指标、趋势分析及 Apple Style 视觉标签

{{ config(
    materialized='table',
    post_hook=[
        "COMMENT ON TABLE {{ this }} IS 'DORA 核心指标大屏预聚合表（包含趋势与评级）'"
    ]
) }}

with base as (
    select * from {{ ref('fct_dora_metrics_v2') }}
),

-- 1. 计算月度趋势 ( lag 窗口函数)
calc_trends as (
    select
        *,
        lag(deployment_frequency) over (partition by product_name order by audit_month) as prev_deploy_freq,
        lag(mttr_hours) over (partition by product_name order by audit_month) as prev_mttr,
        lag(lead_time_hours) over (partition by product_name order by audit_month) as prev_lead_time,
        lag(change_failure_rate_pct) over (partition by product_name order by audit_month) as prev_cfr
    from base
),

-- 2. 选取最新快照
latest_metrics as (
    select
        *,
        row_number() over (partition by product_name order by audit_month desc nulls last) as recency_rank
    from calc_trends
)

select
    product_name,
    coalesce(audit_month, CURRENT_DATE) as last_updated_month,
    
    -- 部署频率 (Higher is better)
    deployment_frequency,
    case 
        when deployment_frequency > coalesce(prev_deploy_freq, 0) then '↑'
        when deployment_frequency < coalesce(prev_deploy_freq, 0) then '↓'
        else '→'
    end as deploy_trend_icon,
    
    -- MTTR (Lower is better)
    mttr_hours,
    case 
        when mttr_hours < coalesce(prev_mttr, 9999) then '↑' -- 向上箭头表示“优化”
        when mttr_hours > coalesce(prev_mttr, 0) then '↓'    -- 向下表示“恶化”
        else '→'
    end as mttr_trend_icon,
    
    -- 前置时间 (Lower is better)
    lead_time_hours,
    case 
        when lead_time_hours < coalesce(prev_lead_time, 9999) then '↑'
        when lead_time_hours > coalesce(prev_lead_time, 0) then '↓'
        else '→'
    end as lead_time_trend_icon,
    
    -- 变更失败率 (Lower is better)
    change_failure_rate_pct,
    case 
        when change_failure_rate_pct < coalesce(prev_cfr, 100) then '↑'
        when change_failure_rate_pct > coalesce(prev_cfr, 0) then '↓'
        else '→'
    end as cfr_trend_icon,

    -- 效能评级 (基于 Lead Time)
    case 
        when lead_time_hours > 0 and lead_time_hours < 24 then 'ELITE'
        when lead_time_hours >= 24 and lead_time_hours < 168 then 'HIGH'
        when lead_time_hours >= 168 and lead_time_hours < 744 then 'MEDIUM'
        else 'LOW'
    end as performance_rating,
    
    -- 视觉健康度 (Apple Style Semantic Colors)
    case 
        when lead_time_hours > 0 and lead_time_hours < 24 then '#34C759' -- Green
        when lead_time_hours >= 24 and lead_time_hours < 168 then '#5856D6' -- Indigo
        when lead_time_hours >= 168 and lead_time_hours < 744 then '#FF9500' -- Orange
        else '#FF3B30' -- Red
    end as health_color_hex

from latest_metrics
where recency_rank = 1

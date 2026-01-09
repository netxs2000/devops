
  
    

  create  table "devops_db"."public_marts"."dws_flow_metrics_weekly__dbt_tmp"
  
  
    as
  
  (
    /*
    DWS: 价值流周效指标 (Value Stream Weekly Metrics)
    
    基于 Flow Framework (Tasktop)，度量业务价值的流动。
    划分四种价值类型：Features, Defects, Debts, Risks.
*/

with 

work_items as (
    select
        *,
        -- 核心价值分类逻辑 (映射自原始类型或标签)
        case 
            when work_item_type in ('Bug', 'Defect', 'Incident') then 'Defect'
            when work_item_type in ('Refactor', 'Tech Debt', 'Cleanup') then 'Debt'
            when work_item_type in ('Security', 'Compliance', 'Risk') then 'Risk'
            else 'Feature'
        end as flow_type
    from "devops_db"."public_intermediate"."int_unified_work_items"
),

weekly_flow as (
    select
        source_project_id as project_id,
        date_trunc('week', closed_at)::date as metric_week,
        flow_type,
        count(*) as items_completed,
        sum(extract(epoch from (closed_at - created_at)) / 86400.0) as sum_flow_time_days
    from work_items
    where closed_at is not null
    group by 1, 2, 3
)

select
    project_id,
    metric_week,
    
    -- Flow Velocity (吞吐量)
    sum(items_completed) as flow_velocity,
    
    -- Flow Distribution (分配分布)
    round(sum(items_completed) filter (where flow_type = 'Feature') * 100.0 / nullif(sum(items_completed), 0), 2) as feature_dist_pct,
    round(sum(items_completed) filter (where flow_type = 'Defect') * 100.0 / nullif(sum(items_completed), 0), 2) as defect_dist_pct,
    round(sum(items_completed) filter (where flow_type = 'Debt') * 100.0 / nullif(sum(items_completed), 0), 2) as debt_dist_pct,
    round(sum(items_completed) filter (where flow_type = 'Risk') * 100.0 / nullif(sum(items_completed), 0), 2) as risk_dist_pct,
    
    -- Flow Time (平均时长)
    round(sum(sum_flow_time_days) / nullif(sum(items_completed), 0), 2) as avg_flow_time_days

from weekly_flow
group by 1, 2
  );
  
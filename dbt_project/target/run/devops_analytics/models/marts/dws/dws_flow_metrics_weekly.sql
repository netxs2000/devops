
  
    

  create  table "devops_db"."public_marts"."dws_flow_metrics_weekly__dbt_tmp"
  
  
    as
  
  (
    /*
    DWS: 价值流周效指标 (Value Stream Weekly Metrics)
    
    基于 Flow Framework (Tasktop)，度量业务价值的流动。
    划分四种价值类型：Features, Defects, Debts, Risks.
*/

with 

flow_items as (
    select * from "devops_db"."public_intermediate"."int_flow_items"
),

weekly_flow as (
    select
        source_project_id as project_id,
        date_trunc('week', closed_at)::date as metric_week,
        count(*) as flow_velocity,
        count(*) filter (where flow_type = 'Feature') as closed_features,
        count(*) filter (where flow_type = 'Defect') as closed_defects,
        count(*) filter (where flow_type = 'Debt') as closed_debts,
        count(*) filter (where flow_type = 'Risk') as closed_risks,
        sum(flow_time_days) as sum_flow_time_days
    from flow_items
    where closed_at is not null
    group by 1, 2
)

select
    project_id,
    metric_week,
    flow_velocity,
    closed_features,
    closed_defects,
    closed_debts,
    closed_risks,
    
    -- Flow Distribution (分配分布比例)
    round(closed_features * 100.0 / nullif(flow_velocity, 0), 2) as feature_dist_pct,
    round(closed_defects * 100.0 / nullif(flow_velocity, 0), 2) as defect_dist_pct,
    round(closed_debts * 100.0 / nullif(flow_velocity, 0), 2) as debt_dist_pct,
    round(closed_risks * 100.0 / nullif(flow_velocity, 0), 2) as risk_dist_pct,
    
    -- Flow Time (平均时长)
    round(sum_flow_time_days / nullif(flow_velocity, 0), 2) as avg_flow_time_days

from weekly_flow
order by metric_week desc
  );
  
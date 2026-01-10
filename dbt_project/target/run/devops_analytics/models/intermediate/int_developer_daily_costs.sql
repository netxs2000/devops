
  create view "devops_db"."public_intermediate"."int_developer_daily_costs__dbt_tmp"
    
    
  as (
    /*
    开发者每日成本核算 (Developer Daily Cost Calculation)
    
    逻辑：
    1. 获取开发者每日活动汇总 (DWS)。
    2. 关联开发者人事成本 (Hourly Rate)。
    3. 按照工作量（目前以活动产出权重或工时计数）分摊每日成本。
*/

with 

dev_activity as (
    select * from "devops_db"."public_marts"."dws_developer_metrics_daily"
),

-- 合并活动与费率
joined as (
    select
        a.user_id,
        a.metric_date,
        a.project_id,
        a.commit_count,
        a.daily_impact_score,
        100.0 as hourly_rate, -- 默认保底费率 (Mocked)
        'CNY' as currency,
        
        -- 分摊逻辑：假设每天标准工时为 8 小时
        -- 如果有具体的工时录入，则使用工时；否则按 8 小时均摊
        8.0 as estimated_hours
        
    from dev_activity a
)

select
    user_id,
    metric_date,
    project_id,
    hourly_rate,
    estimated_hours,
    (hourly_rate * estimated_hours) as daily_cost_amount,
    currency,
    
    -- 派生指标：单位产出成本
    case 
        when commit_count > 0 then (hourly_rate * estimated_hours) / commit_count 
        else null 
    end as cost_per_commit

from joined
  );
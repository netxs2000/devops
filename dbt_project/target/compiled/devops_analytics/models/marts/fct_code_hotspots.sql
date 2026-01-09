/*
    Michael Feathers 代码热点分析 (F-C Analysis)
    
    逻辑：
    1. 维度：Churn (更新频率) vs Complexity (复杂度)。
    2. 目标：识别高频率改动且高复杂度的文件，这些通常是重构的最佳候选对象。
    3. 算法：Risk Factor = Churn * log(Complexity + 2)
*/

with churn_metrics as (
    select * from "devops_db"."public_intermediate"."int_file_churn_metrics"
),

ranked_hotspots as (
    select
        project_id,
        file_path,
        churn_90d,
        churn_30d,
        churn_7d,
        estimated_loc,
        last_modified_at,
        
        -- 计算风险因子
        round(
            churn_90d * log(estimated_loc + 2.0), 
            2
        ) as risk_factor
    from churn_metrics
    where churn_90d > 0
)

select
    *,
    case 
        when risk_factor > 20 and churn_90d > 10 then 'RED_ZONE'  -- 极高风险
        when risk_factor > 10 then 'AMBER_ZONE'                -- 警告
        else 'CLEAR'
    end as risk_zone,
    
    -- 排名
    dense_rank() over (partition by project_id order by risk_factor desc) as project_risk_rank
from ranked_hotspots
order by risk_factor desc
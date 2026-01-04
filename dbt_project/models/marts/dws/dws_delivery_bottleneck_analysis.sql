
/*
    交付瓶颈分析模型 (Delivery Bottleneck Analysis)
    
    逻辑：聚合 MR 各阶段耗时，识别交付流程中的主要停顿点（等待评审 vs 评审协作）。
*/

with lifecycle as (
    select * from {{ ref('int_mr_lifecycle_segments') }}
)

select
    project_id,
    date_trunc('month', merged_at) as audit_month,
    count(distinct merge_request_id) as total_mrs,
    
    -- 阶段平均耗时
    round(avg(pickup_delay_hours)::numeric, 2) as avg_pickup_delay_hours,
    round(avg(review_duration_hours)::numeric, 2) as avg_review_duration_hours,
    round(avg(cycle_time_hours)::numeric, 2) as avg_cycle_time_hours,
    
    -- 瓶颈归类
    case 
        when avg(pickup_delay_hours) > avg(review_duration_hours) then 'WAITING_FOR_REVIEW'
        when avg(review_duration_hours) > 24 then 'COMPLEX_REVIEW_ITERATION'
        else 'HEALTHY_FLOW'
    end as primary_bottleneck
from lifecycle
group by 1, 2

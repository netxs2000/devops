
/*
    指标一致性守护 (Metrics Consistency Guard)
    
    该模型负责检测交付数据中的异常值和不合规模式。
    如果指标数据（如 Cycle Time）超出正常范围，自动将其标记为“不可信”，
    防止脏数据污染决策面板。
*/

with 
base_metrics as (
    -- 假设我们有一张 DORA 指标基础表
    select 
        project_id,
        merge_request_id,
        -- 计算 Lead Time (秒)
        extract(epoch from (merged_at - created_at)) as lead_time_seconds
    from {{ ref('stg_gitlab_merge_requests') }}
    where state = 'merged'
),

stats as (
    -- 计算全局统计量（用于识别 3-sigma 离群值）
    select
        avg(lead_time_seconds) as avg_lt,
        stddev(lead_time_seconds) as std_lt
    from base_metrics
)

select
    m.project_id,
    m.merge_request_id,
    m.lead_time_seconds,
    
    case 
        when m.lead_time_seconds < 0 then 'INVALID_TIME_SEQUENCE'  -- 时间倒流
        when m.lead_time_seconds > (s.avg_lt + 3 * s.std_lt) then 'OUTLIER_TOO_LONG' -- 异常延迟
        when m.lead_time_seconds < 60 then 'SUSPICIOUS_QUICK_MERGE'  -- 疑似秒开秒关（绕过评审）
        else 'TRUSTWORTHY'
    end as data_tag,
    
    case 
        when m.lead_time_seconds < 0 or m.lead_time_seconds > (s.avg_lt + 3 * s.std_lt) then false
        else true
    end as is_metric_valid

from base_metrics m
cross join stats s

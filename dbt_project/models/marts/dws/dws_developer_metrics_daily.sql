
/*
    DWS: 开发者每日指标汇总 (Developer Daily Metrics Summary)
    
    汇总单个开发者在每一天的各项活动产出。
    事实表粒度：用户 + 日期 + 项目
*/

with 

activities as (
    select
        author_user_id as user_id,
        date_trunc('day', occurred_at)::date as metric_date,
        -- 对于统一活动，我们需要解析出 project_id (如果有)
        case 
            when target_entity_type = 'REPO' then target_entity_id 
            else null -- MR/Issue 等可能需要进一步下钻关联
        end as project_id,
        activity_type,
        base_impact_score
    from {{ ref('int_unified_activities') }}
)

select
    user_id,
    metric_date,
    project_id,
    
    -- 原子计数
    count(*) filter (where activity_type = 'COMMIT') as commit_count,
    count(*) filter (where activity_type = 'REVIEW_COMMENT') as review_count,
    count(*) filter (where activity_type = 'MR_OPEN') as mr_open_count,
    count(*) filter (where activity_type = 'MR_MERGE') as mr_merge_count,
    count(*) filter (where activity_type = 'ISSUE_OPEN') as issue_open_count,
    count(*) filter (where activity_type = 'ISSUE_CLOSE') as issue_close_count,
    
    -- 价值评分
    sum(base_impact_score) as daily_impact_score,
    
    -- 活跃度特征
    count(distinct activity_type) as activity_diversity

from activities
group by 1, 2, 3

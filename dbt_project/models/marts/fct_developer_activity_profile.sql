
/*
    开发者 DNA 画像 (Developer Activity Profile)
    
    基于统一活动流，刻画开发者的行为特征：他是“代码机器”、“评审大师”还是“需求终结者”？
*/

with 
activities as (
    select * from {{ ref('int_unified_activities') }}
),

users as (
    select * from {{ ref('stg_mdm_identities') }}
),

profile_stats as (
    select
        author_user_id,
        -- 核心统计
        count(*) filter (where activity_type = 'COMMIT') as commit_count,
        count(*) filter (where activity_type = 'REVIEW_COMMENT') as review_comment_count,
        count(*) filter (where activity_type = 'MR_OPEN') as mr_open_count,
        count(*) filter (where activity_type = 'ISSUE_CLOSE') as issue_closed_count,
        
        -- 加权总分
        sum(base_impact_score) as total_impact_score,
        
        -- 时间特征
        min(occurred_at) as first_active_at,
        max(occurred_at) as last_active_at
    from activities
    group by 1
)

select
    u.user_id,
    u.real_name,
    u.department,
    s.commit_count,
    s.review_comment_count,
    s.mr_open_count,
    s.issue_closed_count,
    s.total_impact_score,
    
    -- 角色判定逻辑
    case 
        when s.review_comment_count > s.commit_count * 2 then 'Review Master'
        when s.commit_count > 50 and s.issue_closed_count < 5 then 'Code Machine'
        when s.issue_closed_count > 20 then 'Task Closer'
        else 'Generalist'
    end as developer_archetype,
    
    round(s.total_impact_score / nullif(extract(epoch from (s.last_active_at - s.first_active_at))/86400, 0)::numeric, 2) as daily_velocity
    
from users u
join profile_stats s on u.user_id = s.author_user_id
where u.is_active = true
order by s.total_impact_score desc

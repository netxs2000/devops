
/*
    影子系统发现 (Shadow IT Discovery)
    
    逻辑：
    1. 识别所有在 GitLab 中活跃但未在 MDM Entity Topology 中对齐的仓库。
    2. 过滤掉已经归档（Archived）或长期无活跃的项目。
    3. 识别潜在的风险点：即那些高活跃度但处于“监管真空”地带的代码资产。
*/

with 
repos as (
    select * from {{ ref('stg_gitlab_projects') }}
    where is_archived = false
),

alignment as (
    select * from {{ ref('int_entity_alignment') }}
    where alignment_strategy = 'UNALIGNED'
),

-- 结合活动流判断活跃度，避免误报死库
recent_activity as (
    select 
        target_entity_id,
        count(*) as total_actions,
        count(distinct author_user_id) as contributor_count,
        max(occurred_at) as last_action_at
    from {{ ref('int_unified_activities') }}
    where occurred_at >= current_date - interval '30 days'
      and target_entity_type = 'REPO'
    group by 1
)

select
    r.gitlab_project_id,
    r.project_name,
    r.path_with_namespace,
    r.created_at,
    ra.total_actions as last_30d_activity_count,
    ra.last_action_at,
    extract(day from (current_timestamp - ra.last_action_at)) as last_activity_days_ago,
    coalesce(ra.contributor_count, 0) as contributor_count,
    'Asset Catalog Missing' as discovery_reason,
    
    -- 风险分级与评分逻辑
    case 
        when ra.total_actions > 100 then 90
        when ra.total_actions > 20 then 50
        else 20
    end as risk_score,

    case 
        when ra.total_actions > 100 then 'HIGH_RISK_SHADOW'
        when ra.total_actions > 20 then 'ACTIVE_UNREGISTERED'
        else 'LOW_PRIORITY_UNREGISTERED'
    end as shadow_it_status

from alignment a
join repos r on a.gitlab_project_id = r.gitlab_project_id
left join recent_activity ra on r.gitlab_project_id::text = ra.target_entity_id
where ra.total_actions > 0 -- 至少有一点活跃才叫影子系统，否则只是僵尸项目
order by ra.total_actions desc

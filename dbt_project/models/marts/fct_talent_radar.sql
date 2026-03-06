
/*
    人才雷达/技术画像模型 (Developer Talent Radar)
    
    量化维度：
    1. 活跃度：最近 90 天的 Commit 分布。
    2. 深度：核心/关键资产的参与度 (Critical Assets)。
    3. 广度：跨项目的协作能力。
*/

with 

commits as (
    select 
        master_user_id as user_id,
        project_id,
        committed_at as committed_date
    from {{ ref('int_commits_with_authors') }}
),

asset_weights as (
    -- 为不同重要性的资产分配分数权重
    select 
        user_id,
        count(distinct project_id) as active_repo_count,
        sum(case when et.element_type = 'source-code' then 1 else 0 end) as asset_score -- 简化权重逻辑，后续可根据 topology 扩展
    from commits c
    left join {{ ref('stg_mdm_entity_topology') }} et 
        on c.project_id::text = et.external_resource_id
    where c.committed_date >= current_date - interval '90 days'
    group by 1
),

final as (
    select
        u.global_user_id,
        u.full_name,
        u.department_name,
        coalesce(a.active_repo_count, 0) as active_repo_count,
        coalesce(a.asset_score, 0) as talent_score
    from {{ ref('int_golden_identity') }} u
    left join asset_weights a on u.global_user_id = a.user_id
)

select * from final

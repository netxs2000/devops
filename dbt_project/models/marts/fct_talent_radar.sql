
/* 
    人才隐形影响力雷达 (Talent Influence Radar)
    
    量化开发者的 "Technical Leadership" 和 "Implicit Impact"。
    不看堆代码量，看核心贡献、评审参与度和跨域影响。
*/

with 
-- 1. 评审影响力 (Review)
reviewer_stats as (
    -- 这里假设 stg_gitlab_merge_requests 已经包含了 reviewer 信息
    -- 实际场景中可能需要一张独立的 reviewers 关联表 source('raw', 'gitlab_mr_reviewers')
    select 
        author_user_id as user_id, -- 简化目前使用 author 作为示例，实际应 join reviewer 表
        count(distinct merge_request_id) as review_count,
        count(distinct merge_request_id) * 2.0 as review_score
    from {{ ref('stg_gitlab_merge_requests') }}
    where created_at >= current_date - interval '90 days'
    group by 1
),

-- 2. 核心资产控制力 (Asset Impact)
asset_impact_stats as (
    select 
        c.author_user_id as user_id,
        count(distinct c.project_id) as critical_repo_count,
        -- 通过 EntityTopology 判断是否为 Critical 资产
        sum(case when et.importance = 'Critical' then 5 else 1 end) as asset_score
    from {{ ref('int_commits_with_authors') }} c
    join {{ ref('stg_mdm_entities_topology') }} et 
        on c.project_id::text = et.internal_id and et.entity_type = 'REPO'
    where c.committed_date >= current_date - interval '90 days'
    group by 1
),

-- 3. 用户主数据
users as (
    select * from {{ ref('stg_mdm_identities') }}
)

-- 4. 最终汇聚
select
    u.user_id,
    u.real_name,
    u.department,
    coalesce(rs.review_count, 0) as metric_reviews,
    coalesce(ais.critical_repo_count, 0) as metric_critical_repos,
    
    -- 综合影响力指数
    round(
        (coalesce(rs.review_score, 0) * 0.4) + 
        (coalesce(ais.asset_score, 0) * 0.6)
    , 2) as talent_influence_index

from users u
left join reviewer_stats rs on u.user_id = rs.user_id
left join asset_impact_stats ais on u.user_id = ais.user_id
where u.is_active = true
order by talent_influence_index desc

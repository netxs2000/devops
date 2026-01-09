/* 
    人才隐形影响力雷达 (Talent Influence Radar) v2.0
    
    量化开发者的 "Technical Leadership" 和 "Implicit Impact"。
    不看堆代码量，看核心贡献、评审参与度和【知识领域控制深度】。
*/

with 
-- 1. 评审影响力 (Review)
reviewer_stats as (
    select 
        u.master_user_id as user_id,
        count(distinct n.note_id) as review_comment_count,
        count(distinct n.note_id) * 3.0 as review_score
    from "devops_db"."public_staging"."stg_gitlab_notes" n
    join "devops_db"."public_intermediate"."int_gitlab_user_mapping" u on n.author_user_id::text = u.gitlab_user_id
    where n.noteable_type = 'MergeRequest'
      and n.created_at >= current_date - interval '90 days'
    group by 1
),

-- 2. 核心资产控制力 (Asset Impact)
asset_impact_stats as (
    select 
        c.author_user_id as user_id,
        count(distinct c.project_id) as active_repo_count,
        sum(case when et.importance = 'Critical' then 5 else 1 end) as asset_score
    from "devops_db"."public_intermediate"."int_commits_with_authors" c
    left join "devops_db"."public_staging"."stg_mdm_entities_topology" et 
        on c.project_id::text = et.internal_id and et.entity_type = 'REPO'
    where c.committed_date >= current_date - interval '90 days'
    group by 1
),

-- 3. 知识领地深度 (Knowledge Domain Depth) - 基于所有历史贡献
knowledge_depth as (
    select
        author_user_id as user_id,
        count(distinct subsystem) as owned_subsystems_count,
        sum(case when knowledge_risk_status = 'KNOWLEDGE_SILO' then 10 else 2 end) as domain_depth_score
    from "devops_db"."public_marts"."dws_subsystem_bus_factor"
    where subsystem_ownership_pct > 30 -- 有一定话语权
    group by 1
),

-- 4. 用户主数据
users as (
    select * from "devops_db"."public_staging"."stg_mdm_identities"
)

-- 5. 最终汇聚
select
    u.user_id,
    u.real_name,
    u.department,
    coalesce(rs.review_comment_count, 0) as metric_review_comments,
    coalesce(ais.active_repo_count, 0) as metric_active_repos,
    coalesce(kd.owned_subsystems_count, 0) as metric_knowledge_domains,
    
    -- 核心画像标签
    case 
        when kd.domain_depth_score > 50 then 'Domain Specialist'
        when rs.review_score > 30 then 'Collaborative Leader'
        when ais.asset_score > 20 then 'Reliable Contributor'
        else 'Active Engineer'
    end as talent_archetype,

    -- 综合影响力指数 (Multi-Dimensional Index)
    round(
        (coalesce(rs.review_score, 0) * 0.3) + 
        (coalesce(ais.asset_score, 0) * 0.3) +
        (coalesce(kd.domain_depth_score, 0) * 0.4)
    , 2) as talent_influence_index

from users u
left join reviewer_stats rs on u.user_id = rs.user_id
left join asset_impact_stats ais on u.user_id = ais.user_id
left join knowledge_depth kd on u.user_id = kd.user_id
where u.is_active = true
order by talent_influence_index desc
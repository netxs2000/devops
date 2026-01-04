
/*
    DWS: 团队效能周报模型 (Team Efficiency Weekly Summary)
    
    视角：中层管理者 (Director/Dept Manager)
    目标：监控团队整体吞吐量、交付速度与质量趋势。
    粒度：组织 ID + 自然周 (ISO Week)
*/

with 

-- 1. 基础日度指标
daily_metrics as (
    select * from {{ ref('dws_developer_metrics_daily') }}
),

-- 2. 人员与部门映射 (SCD Type 2 考虑)
user_org as (
    select 
        user_id,
        department_id
    from {{ ref('stg_mdm_identities') }}
),

-- 3. 组织树路径增强
org_hierarchy as (
    select * from {{ ref('int_org_hierarchy') }}
),

-- 4. 关联用户到部门路径
enriched_activities as (
    select
        dm.*,
        uo.department_id,
        oh.full_path as team_path,
        oh.org_name as team_name,
        oh.root_org_name
    from daily_metrics dm
    left join user_org uo on dm.user_id = uo.user_id
    left join org_hierarchy oh on uo.department_id = oh.org_id
),

-- 5. 按周聚合团队指标
weekly_aggregation as (
    select
        date_trunc('week', metric_date)::date as audit_week,
        department_id,
        team_name,
        team_path,
        root_org_name,
        
        -- 规模指标 (Capacity)
        count(distinct user_id) as active_developer_count,
        
        -- 交付产出 (Throughput)
        sum(commit_count) as total_commits,
        sum(mr_merge_count) as total_merges,
        sum(issue_close_count) as total_issues_resolved,
        
        -- 价值评分
        sum(daily_impact_score) as total_impact_score,
        
        -- 协作特征 (Collaboration)
        sum(review_count) as total_reviews,
        round(cast(sum(review_count) as numeric) / nullif(sum(mr_merge_count), 0), 2) as review_per_merge,
        
        -- 统计范围
        count(distinct project_id) as associated_project_count

    from enriched_activities
    group by 1, 2, 3, 4, 5
)

select * from weekly_aggregation

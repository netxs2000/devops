
  create view "devops_db"."public_intermediate"."int_mr_lifecycle_segments__dbt_tmp"
    
    
  as (
    /*
    MR 生命周期打点模型 (MR Lifecycle Segments)
    
    逻辑：计算 MR 从创建到合并过程中各个关键节点的耗时。
    1. Pick-up Time: 创建到首次人工评论。
    2. Review Time: 首次评论到合并。
    3. Cycle Time: 创建到合并总量。
*/

with mrs as (
    select * from "devops_db"."public_staging"."stg_gitlab_merge_requests"
    where state = 'merged'
),

notes as (
    select * from "devops_db"."public_staging"."stg_gitlab_notes"
    where noteable_type = 'MergeRequest'
),

first_interactions as (
    select
        noteable_iid as merge_request_iid, -- DB has noteable_iid for GitLab notes
        min(created_at) as first_human_comment_at
    from notes
    group by 1
),

lifecycle as (
    select
        m.merge_request_id,
        m.project_id,
        m.created_at,
        m.merged_at,
        f.first_human_comment_at,
        
        -- 段 1: 等待评审时间 (Pick-up Time)
        extract(epoch from (coalesce(f.first_human_comment_at, m.merged_at) - m.created_at)) / 3600.0 as pickup_delay_hours,
        
        -- 段 2: 评审迭代时间 (Review Time)
        case 
            when f.first_human_comment_at is not null then extract(epoch from (m.merged_at - f.first_human_comment_at)) / 3600.0
            else 0 
        end as review_duration_hours,
        
        -- 总计耗时 (Cycle Time)
        extract(epoch from (m.merged_at - m.created_at)) / 3600.0 as cycle_time_hours
    from mrs m
    left join first_interactions f on m.iid = f.merge_request_iid
)

select * from lifecycle
  );
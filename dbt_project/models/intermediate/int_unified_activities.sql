
/*
    统一活动流引擎 (Unified Activity Stream Engine)
    
    该模型将来自不同工具的所有原子操作（Commits, MRs, Issues, Comments）
    打平为一个标准的、可度量的事件流。
    
    它是计算“开发者画像”、 “团队负荷”和“交付前导时间”的基础。
*/

with 

-- 1. 开发活动 (Commits)
commit_activities as (
    select
        commit_sha as activity_id,
        committed_date as occurred_at,
        author_user_id,
        'COMMIT' as activity_type,
        project_id::text as target_entity_id,
        'REPO' as target_entity_type,
        1.0 as base_impact_score,
        'GITLAB' as source_system,
        json_build_object('sha', commit_sha, 'title', title) as metadata
    from {{ ref('int_commits_with_authors') }}
),

-- 2. 协作活动 (Merge Requests)
mr_activities as (
    select
        merge_request_id::text as activity_id,
        created_at as occurred_at,
        author_user_id,
        'MR_OPEN' as activity_type,
        merge_request_id::text as target_entity_id,
        'MR' as target_entity_type,
        2.0 as base_impact_score,
        'GITLAB' as source_system,
        json_build_object('iid', iid, 'title', title) as metadata
    from {{ ref('stg_gitlab_merge_requests') }}
    
    union all
    
    select
        merge_request_id::text || '_merged' as activity_id,
        merged_at as occurred_at,
        merged_by_user_id as author_user_id,
        'MR_MERGE' as activity_type,
        merge_request_id::text as target_entity_id,
        'MR' as target_entity_type,
        3.0 as base_impact_score,
        'GITLAB' as source_system,
        json_build_object('iid', iid, 'title', title) as metadata
    from {{ ref('stg_gitlab_merge_requests') }}
    where state = 'merged'
),

-- 3. 需求/任务活动 (Issues)
issue_activities as (
    select
        issue_id::text as activity_id,
        created_at as occurred_at,
        author_user_id,
        'ISSUE_OPEN' as activity_type,
        issue_id::text as target_entity_id,
        'ISSUE' as target_entity_type,
        1.0 as base_impact_score,
        'GITLAB' as source_system,
        json_build_object('iid', iid, 'title', title) as metadata
    from {{ ref('stg_gitlab_issues') }}
    
    union all
    
    select
        issue_id::text || '_closed' as activity_id,
        closed_at as occurred_at,
        author_user_id, -- 这里假设关闭者是原作者，实际应使用 closed_by 字段
        'ISSUE_CLOSE' as activity_type,
        issue_id::text as target_entity_id,
        'ISSUE' as target_entity_type,
        1.5 as base_impact_score,
        'GITLAB' as source_system,
        json_build_object('iid', iid, 'title', title) as metadata
    from {{ ref('stg_gitlab_issues') }}
    where state = 'closed'
),

-- 4. 评审/讨论活动 (Notes/Comments)
note_activities as (
    select
        note_id::text as activity_id,
        created_at as occurred_at,
        author_user_id,
        case 
            when noteable_type = 'MergeRequest' then 'REVIEW_COMMENT'
            else 'ISSUE_DISCUSSION'
        end as activity_type,
        noteable_id::text as target_entity_id,
        noteable_type as target_entity_type,
        2.0 as base_impact_score,
        'GITLAB' as source_system,
        json_build_object('body_snippet', left(body, 50)) as metadata
    from {{ ref('stg_gitlab_notes') }}
)

-- 5. 最终汇聚 (The Stream)
select * from commit_activities
union all
select * from mr_activities
union all
select * from issue_activities
union all
select * from note_activities
order by occurred_at desc

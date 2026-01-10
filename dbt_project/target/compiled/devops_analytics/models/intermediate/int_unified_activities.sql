/*
    统一活动流引擎 (Unified Activity Stream Engine)
    
    该模型将来自不同工具的所有原子操作（Commits, MRs, Issues, Comments）
    打平为一个标准的、可度量的事件流。
    
    它是计算“开发者画像”、 “团队负荷”和“交付前导时间”的基础。
*/


with 

-- 辅助映射模型
gitlab_users as (
    select * from "devops_db"."public_intermediate"."int_gitlab_user_mapping"
),

identities as (
    select * from "devops_db"."public_staging"."stg_mdm_identities"
),

-- 1. 开发活动 (Commits)
-- 注意：int_commits_with_authors 内部已经完成了校准，直接使用
commit_activities as (
    select
        commit_sha as activity_id,
        committed_date as occurred_at,
        author_user_id,
        'COMMIT' as activity_type,
        project_id::text as target_entity_id,
        project_id,
        'REPO' as target_entity_type,
        1.0 as base_impact_score,
        'GITLAB' as source_system,
        title as summary,
        json_build_object('sha', commit_sha, 'title', title) as metadata
    from "devops_db"."public_intermediate"."int_commits_with_authors"
),

-- 2. 协作活动 (Merge Requests)
mr_activities as (
    select
        m.merge_request_id::text as activity_id,
        m.created_at as occurred_at,
        coalesce(u.master_user_id, '00000000-0000-0000-0000-000000000000'::uuid) as author_user_id,
        'MR_OPEN' as activity_type,
        m.merge_request_id::text as target_entity_id,
        m.project_id,
        'MR' as target_entity_type,
        2.0 as base_impact_score,
        'GITLAB' as source_system,
        m.title as summary,
        json_build_object('iid', m.iid, 'title', m.title) as metadata
    from "devops_db"."public_staging"."stg_gitlab_merge_requests" m
    left join gitlab_users u on m.author_user_id::text = u.gitlab_user_id
    
    union all
    
    select
        m.merge_request_id::text || '_merged' as activity_id,
        m.merged_at as occurred_at,
        coalesce(u.master_user_id, '00000000-0000-0000-0000-000000000000'::uuid) as author_user_id,
        'MR_MERGE' as activity_type,
        m.merge_request_id::text as target_entity_id,
        m.project_id,
        'MR' as target_entity_type,
        3.0 as base_impact_score,
        'GITLAB' as source_system,
        m.title as summary,
        json_build_object('iid', m.iid, 'title', m.title) as metadata
    from "devops_db"."public_staging"."stg_gitlab_merge_requests" m
    -- merged_by_user_id is missing in DB, fallback to author_user_id for now or leave as unknown
    left join gitlab_users u on m.author_user_id::text = u.gitlab_user_id
    where m.state = 'merged' and m.merged_at is not null
),

-- 3. 需求/任务活动 (Issues)
issue_activities as (
    select
        i.issue_id::text as activity_id,
        i.created_at as occurred_at,
        coalesce(u.master_user_id, '00000000-0000-0000-0000-000000000000'::uuid) as author_user_id,
        'ISSUE_OPEN' as activity_type,
        i.issue_id::text as target_entity_id,
        i.project_id,
        'ISSUE' as target_entity_type,
        1.0 as base_impact_score,
        'GITLAB' as source_system,
        i.title as summary,
        json_build_object('iid', i.iid, 'title', i.title) as metadata
    from "devops_db"."public_staging"."stg_gitlab_issues" i
    left join gitlab_users u on i.author_user_id::text = u.gitlab_user_id
    
    union all
    
    select
        i.issue_id::text || '_closed' as activity_id,
        i.closed_at as occurred_at,
        coalesce(u.master_user_id, '00000000-0000-0000-0000-000000000000'::uuid) as author_user_id,
        'ISSUE_CLOSE' as activity_type,
        i.issue_id::text as target_entity_id,
        i.project_id,
        'ISSUE' as target_entity_type,
        1.5 as base_impact_score,
        'GITLAB' as source_system,
        i.title as summary,
        json_build_object('iid', i.iid, 'title', i.title) as metadata
    from "devops_db"."public_staging"."stg_gitlab_issues" i
    -- 这里我们假设关闭者映射到原作者
    left join gitlab_users u on i.author_user_id::text = u.gitlab_user_id
    where i.state = 'closed' and i.closed_at is not null
),

-- 4. 评审/讨论活动 (Notes/Comments)
note_activities as (
    select
        n.note_id::text as activity_id,
        n.created_at as occurred_at,
        coalesce(u.master_user_id, '00000000-0000-0000-0000-000000000000'::uuid) as author_user_id,
        case 
            when n.noteable_type = 'MergeRequest' then 'REVIEW_COMMENT'
            else 'ISSUE_DISCUSSION'
        end as activity_type,
        n.noteable_iid::text as target_entity_id, -- Use noteable_iid
        n.project_id,
        n.noteable_type as target_entity_type,
        2.0 as base_impact_score,
        'GITLAB' as source_system,
        left(n.body, 100) as summary,
        json_build_object('body_snippet', left(n.body, 50)) as metadata
    from "devops_db"."public_staging"."stg_gitlab_notes" n
    left join gitlab_users u on n.author_user_id::text = u.gitlab_user_id
),

-- 5. 最终汇聚 (The Stream)
unified_stream as (
    select * from commit_activities
    union all
    select * from mr_activities
    union all
    select * from issue_activities
    union all
    select * from note_activities
)

select 
    s.*,
    coalesce(i.real_name, 'Unknown') as author_name
from unified_stream s
left join identities i on s.author_user_id = i.user_id
order by s.occurred_at desc
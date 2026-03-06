{{
    config(
        materialized='incremental',
        unique_key='activity_id',
        on_schema_change='append_new_columns'
    )
}}

with 

-- 辅助映射模型
gitlab_users as (
    select * from {{ ref('int_gitlab_user_mapping') }}
),

identities as (
    select * from {{ ref('stg_mdm_identities') }}
),

-- 1. 开发活动 (Commits)
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
    from {{ ref('int_commits_with_authors') }}
    {% if is_incremental() %}
    where committed_date >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}
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
    from {{ ref('stg_gitlab_merge_requests') }} m
    left join gitlab_users u on m.author_user_id::text = u.gitlab_user_id
    {% if is_incremental() %}
    where m.created_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}

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
    from {{ ref('stg_gitlab_merge_requests') }} m
    left join gitlab_users u on m.author_user_id::text = u.gitlab_user_id
    where m.state = 'merged' and m.merged_at is not null
    {% if is_incremental() %}
    and m.merged_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}
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
    from {{ ref('stg_gitlab_issues') }} i
    left join gitlab_users u on i.author_user_id::text = u.gitlab_user_id
    {% if is_incremental() %}
    where i.created_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}

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
    from {{ ref('stg_gitlab_issues') }} i
    left join gitlab_users u on i.author_user_id::text = u.gitlab_user_id
    where i.state = 'closed' and i.closed_at is not null
    {% if is_incremental() %}
    and i.closed_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}
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
        n.noteable_iid::text as target_entity_id,
        n.project_id,
        n.noteable_type as target_entity_type,
        2.0 as base_impact_score,
        'GITLAB' as source_system,
        left(n.body, 100) as summary,
        json_build_object('body_snippet', left(n.body, 50)) as metadata
    from {{ ref('stg_gitlab_notes') }} n
    left join gitlab_users u on n.author_user_id::text = u.gitlab_user_id
    {% if is_incremental() %}
    where n.created_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}
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

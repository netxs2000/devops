{{
    config(
        materialized='incremental',
        unique_key='activity_id',
        on_schema_change='append_new_columns'
    )
}}

with 

-- 1. 开发活动 (Commits)
commit_activities as (
    select
        'GITLAB-COMMIT-' || commit_sha as activity_id,
        committed_date as occurred_at,
        lower(trim(author_email)) as external_author_id,
        'EMAIL' as identifier_type,
        'COMMIT' as activity_type,
        project_id::text as target_entity_id,
        project_id,
        'REPO' as target_entity_type,
        1.0 as base_impact_score,
        'GITLAB' as source_system,
        title as summary,
        json_build_object('sha', commit_sha, 'title', title) as metadata
    from {{ ref('stg_gitlab_commits') }}
    {% if is_incremental() %}
    where committed_date >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}
),

-- 2. 协作活动 (Merge Requests)
mr_activities as (
    select
        'GITLAB-MR-OPEN-' || m.merge_request_id::text as activity_id,
        m.created_at as occurred_at,
        m.author_user_id::text as external_author_id,
        'EXTERNAL_ID' as identifier_type,
        'MR' as activity_type,
        m.merge_request_id::text as target_entity_id,
        m.project_id,
        'MR' as target_entity_type,
        2.0 as base_impact_score,
        'GITLAB' as source_system,
        m.title as summary,
        json_build_object('iid', m.iid, 'title', m.title) as metadata
    from {{ ref('stg_gitlab_merge_requests') }} m
    {% if is_incremental() %}
    where m.created_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}

    union all
    
    select
        'GITLAB-MR-MERGE-' || m.merge_request_id::text as activity_id,
        m.merged_at as occurred_at,
        m.author_user_id::text as external_author_id,
        'EXTERNAL_ID' as identifier_type,
        'MR' as activity_type,
        m.merge_request_id::text as target_entity_id,
        m.project_id,
        'MR' as target_entity_type,
        3.0 as base_impact_score,
        'GITLAB' as source_system,
        m.title as summary,
        json_build_object('iid', m.iid, 'title', m.title) as metadata
    from {{ ref('stg_gitlab_merge_requests') }} m
    where m.state = 'merged' and m.merged_at is not null
    {% if is_incremental() %}
    and m.merged_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}
),

-- 3. 需求/任务活动 (Issues)
issue_activities as (
    select
        'GITLAB-ISSUE-OPEN-' || i.issue_id::text as activity_id,
        i.created_at as occurred_at,
        i.author_user_id::text as external_author_id,
        'EXTERNAL_ID' as identifier_type,
        'ISSUE' as activity_type,
        i.issue_id::text as target_entity_id,
        i.project_id,
        'ISSUE' as target_entity_type,
        1.0 as base_impact_score,
        'GITLAB' as source_system,
        i.title as summary,
        json_build_object('iid', i.iid, 'title', i.title) as metadata
    from {{ ref('stg_gitlab_issues') }} i
    {% if is_incremental() %}
    where i.created_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}

    union all
    
    select
        'GITLAB-ISSUE-CLOSE-' || i.issue_id::text as activity_id,
        i.closed_at as occurred_at,
        i.author_user_id::text as external_author_id,
        'EXTERNAL_ID' as identifier_type,
        'ISSUE' as activity_type,
        i.issue_id::text as target_entity_id,
        i.project_id,
        'ISSUE' as target_entity_type,
        1.5 as base_impact_score,
        'GITLAB' as source_system,
        i.title as summary,
        json_build_object('iid', i.iid, 'title', i.title) as metadata
    from {{ ref('stg_gitlab_issues') }} i
    where i.state = 'closed' and i.closed_at is not null
    {% if is_incremental() %}
    and i.closed_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}
),

-- 4. 评审/讨论活动 (Notes/Comments)
note_activities as (
    select
        'GITLAB-NOTE-' || n.note_id::text as activity_id,
        n.created_at as occurred_at,
        n.author_user_id::text as external_author_id,
        'EXTERNAL_ID' as identifier_type,
        'REVIEW' as activity_type,
        n.noteable_iid::text as target_entity_id,
        n.project_id,
        n.noteable_type as target_entity_type,
        2.0 as base_impact_score,
        'GITLAB' as source_system,
        left(n.body, 100) as summary,
        json_build_object('body_snippet', left(n.body, 50)) as metadata
    from {{ ref('stg_gitlab_notes') }} n
    {% if is_incremental() %}
    where n.created_at >= (select max(occurred_at) - interval '3 days' from {{ this }})
    {% endif %}
)

-- 5. 最终汇聚 (The Stream)
select * from commit_activities
union all
select * from mr_activities
union all
select * from issue_activities
union all
select * from note_activities

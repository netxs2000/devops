
/*
    统一工作项引擎 (Unified Work Items Engine)
    
    该模型整合了来自 Jira 和 GitLab 的所有任务、需求和缺陷。
    它是进行跨部门进度分析、交付节奏度量和 ROI 核算的核心基础。
*/

with 

-- 1. 来自 Jira 的工作项
jira_items as (
    select
        id::text as work_item_id,
        key as work_item_key,
        project_id::text as source_project_id,
        summary as title,
        status as current_status,
        issue_type as work_item_type,
        created_at,
        updated_at,
        resolved_at as closed_at,
        assignee_user_id as author_user_id, -- 简化归责
        'JIRA' as source_system,
        original_estimate as estimate_seconds,
        time_spent as spent_seconds
    from {{ source('raw', 'jira_issues') }}
),

-- 2. 来自 GitLab 的工作项
gitlab_items as (
    select
        issue_id::text as work_item_id,
        iid::text as work_item_key,
        project_id::text as source_project_id,
        title,
        state as current_status,
        'Issue' as work_item_type,
        created_at,
        updated_at,
        closed_at,
        author_user_id,
        'GITLAB' as source_system,
        time_estimate as estimate_seconds,
        total_time_spent as spent_seconds
    from {{ ref('stg_gitlab_issues') }}
)

-- 3. 最终汇总
select * from jira_items
union all
select * from gitlab_items

/*
    合规与内控审计 (Governance & Compliance Audit)
    
    逻辑：
    1. 四眼原则 (Four-Eyes Principle): 统计未经过独立评审（除作者外无评论）就合并的 MR。
    2. 直连推送 (Direct Pushes): 识别未通过 MR 流程直接进入主干的代码行为（演示逻辑）。
    3. 职责分离 (SoD): 识别既是开发者又是审批者的风险（简化版）。
*/

with 

-- 1. 四眼原则分析
mr_reviews as (
    select 
        mr.merge_request_id,
        mr.author_user_id,
        count(distinct n.author_user_id) filter (where n.author_user_id != mr.author_user_id) as independent_reviewer_count
    from "devops_db"."public_staging"."stg_gitlab_merge_requests" mr
    left join "devops_db"."public_staging"."stg_gitlab_notes" n 
        on mr.merge_request_id = n.noteable_id 
        and n.noteable_type = 'MergeRequest'
    where mr.state = 'merged'
    group by 1, 2
),

-- 2. 直连推送分析 (基于 Commit 且不在任何 MR 的 Merge SHA 中)
-- 这是一个简化的启发式逻辑
direct_pushes as (
    select 
        c.project_id,
        count(*) as direct_push_count
    from "devops_db"."public_staging"."stg_gitlab_commits" c
    left join "devops_db"."public_staging"."stg_gitlab_merge_requests" mr on c.commit_sha = mr.merge_commit_sha
    where mr.merge_request_id is null
      and c.title not ilike 'merge branch%' -- 排除手工 merge 产生的 commit
    group by 1
)

select
    p.project_name,
    p.path_with_namespace,
    
    -- 四眼原则
    count(mr.merge_request_id) as total_merged_mrs,
    count(mr.merge_request_id) filter (where rev.independent_reviewer_count = 0) as suspicious_bypass_mrs,
    round(
        (count(mr.merge_request_id) filter (where rev.independent_reviewer_count = 0))::numeric 
        / nullif(count(mr.merge_request_id), 0) * 100, 2
    ) as bypass_rate_pct,
    
    -- 直连推送
    coalesce(dp.direct_push_count, 0) as direct_push_incidents,
    
    -- 合规评级
    case 
        when (count(mr.merge_request_id) filter (where rev.independent_reviewer_count = 0))::numeric / nullif(count(mr.merge_request_id), 0) > 0.3 then 'NON_COMPLIANT'
        when coalesce(dp.direct_push_count, 0) > 10 then 'PROCESS_RISK'
        else 'COMPLIANT'
    end as compliance_status

from "devops_db"."public_staging"."stg_gitlab_projects" p
join "devops_db"."public_staging"."stg_gitlab_merge_requests" mr on p.gitlab_project_id = mr.project_id
left join mr_reviews rev on mr.merge_request_id = rev.merge_request_id
left join direct_pushes dp on p.gitlab_project_id = dp.project_id
where mr.state = 'merged'
group by p.project_name, p.path_with_namespace, dp.direct_push_count
order by bypass_rate_pct desc
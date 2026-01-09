
with file_stats as (
    select * from {{ ref('stg_gitlab_commit_file_stats') }}
),

commits as (
    select * from {{ ref('stg_gitlab_commits') }}
),

joined as (
    select
        f.file_path,
        c.project_id,
        c.committed_date,
        f.commit_id,
        f.code_added,
        f.code_deleted
    from file_stats f
    join commits c on f.commit_id = c.commit_sha
    where f.file_path not like '%.json'
      and f.file_path not like '%.lock'
      and f.file_path not like '%.md'
      and f.file_path not like '%.txt'
)

select
    project_id,
    file_path,
    -- 90天内的变更频率 (Churn)
    count(distinct case when committed_date >= current_date - interval '90 days' then commit_id end) as churn_90d,
    -- 30天内的变更频率
    count(distinct case when committed_date >= current_date - interval '30 days' then commit_id end) as churn_30d,
    -- 7天内的变更频率
    count(distinct case when committed_date >= current_date - interval '7 days' then commit_id end) as churn_7d,
    
    -- 预估行数 (Complexity Proxy)
    abs(sum(code_added) - sum(code_deleted)) as estimated_loc,
    
    max(committed_date) as last_modified_at
from joined
group by 1, 2
having abs(sum(code_added) - sum(code_deleted)) > 10

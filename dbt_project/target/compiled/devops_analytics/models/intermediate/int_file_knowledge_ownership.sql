with file_stats as (
    select * from "devops_db"."public_staging"."stg_gitlab_commit_file_stats"
),

commits as (
    select * from "devops_db"."public_intermediate"."int_commits_with_authors"
),

file_contributions as (
    select
        f.file_path,
        c.project_id,
        c.author_user_id,
        sum(f.code_added) as lines_added
    from file_stats f
    join commits c on f.commit_id = c.commit_sha
    group by 1, 2, 3
),

file_totals as (
    select
        file_path,
        project_id,
        sum(lines_added) as total_lines_added
    from file_contributions
    group by 1, 2
)

select
    c.file_path,
    c.project_id,
    c.author_user_id,
    c.lines_added,
    t.total_lines_added,
    case 
        when t.total_lines_added > 0 then round(c.lines_added * 100.0 / t.total_lines_added, 2)
        else 0 
    end as ownership_pct
from file_contributions c
join file_totals t on c.file_path = t.file_path and c.project_id = t.project_id
where t.total_lines_added > 0
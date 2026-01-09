with file_ownership as (
    select * from "devops_db"."public_intermediate"."int_file_knowledge_ownership"
),

-- 提取子系统 (Top-level directory)
subsystem_stats as (
    select
        project_id,
        author_user_id,
        -- 取路径的前两级作为子系统标识
        case 
            when position('/' in file_path) > 0 then split_part(file_path, '/', 1)
            else 'root'
        end as subsystem,
        sum(lines_added) as subsystem_lines
    from file_ownership
    group by 1, 2, 3
),

subsystem_totals as (
    select
        project_id,
        subsystem,
        sum(subsystem_lines) as total_subsystem_lines,
        count(distinct author_user_id) as contributor_count
    from subsystem_stats
    group by 1, 2
),

ownership_details as (
    select
        s.project_id,
        s.subsystem,
        s.author_user_id,
        s.subsystem_lines,
        t.total_subsystem_lines,
        t.contributor_count,
        round(s.subsystem_lines * 100.0 / t.total_subsystem_lines, 2) as subsystem_ownership_pct
    from subsystem_stats s
    join subsystem_totals t on s.project_id = t.project_id and s.subsystem = t.subsystem
)

select
    *,
    case 
        when subsystem_ownership_pct > 80 then 'KNOWLEDGE_SILO'
        when contributor_count = 1 then 'TRUCK_FACTOR_ONE'
        else 'HEALTHY_DISTRIBUTION'
    end as knowledge_risk_status
from ownership_details
where subsystem != 'root' or total_subsystem_lines > 1000
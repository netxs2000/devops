-- Branch Operations View
-- Lists active branches with their activity status.
-- Note: "Creation Time" is approximated by "Last Commit Date" as Git branches are mutable pointers.
-- "Creator" is approximated by "Last Committer".

CREATE OR REPLACE VIEW view_branch_ops AS
SELECT
    p.name as project_name,
    b.name as branch_name,
    
    -- Activity Info
    b.last_commit_date as latest_activity_at,
    b.last_committer_name as latest_committer,
    
    -- Branch Status
    b.is_default,
    b.is_protected,
    b.is_merged,
    
    -- Age Calculation (Days since last activity)
    EXTRACT(DAY FROM (NOW() - b.last_commit_date)) as days_inactive

FROM branches b
JOIN projects p ON b.project_id = p.id
ORDER BY b.last_commit_date DESC;

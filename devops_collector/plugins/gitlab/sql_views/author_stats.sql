-- Author Stats View (Detailed Table)
-- Matches the "Authors" table requirement:
-- Columns: Author, Commits, Lines added, Lines removed, First commit, Last commit, Age(Days), Active days, Mrs

CREATE OR REPLACE VIEW view_author_stats AS
SELECT 
    u.id as user_id,
    u.name as author_name,
    u.department,
    
    -- 1. Commits & Lines
    COUNT(c.id) as commits_count,
    SUM(c.additions) as lines_added,
    SUM(c.deletions) as lines_removed,
    
    -- 2. Time Range
    MIN(c.authored_date) as first_commit_date,
    MAX(c.authored_date) as last_commit_date,
    
    -- 3. Age (Days between First and Last)
    EXTRACT(DAY FROM (MAX(c.authored_date) - MIN(c.authored_date))) as age_days,
    
    -- 4. Active Days (Count of unique days with commits)
    COUNT(DISTINCT date_trunc('day', c.authored_date)) as active_days_count,
    
    -- 5. Merge Requests (Count of MRs authored)
    COUNT(DISTINCT mr.id) as mr_count

FROM users u
LEFT JOIN commits c ON u.id = c.gitlab_user_id
LEFT JOIN merge_requests mr ON u.id = mr.author_id
GROUP BY u.id, u.name, u.department
ORDER BY commits_count DESC;

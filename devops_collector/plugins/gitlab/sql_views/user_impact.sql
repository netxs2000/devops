-- User Contribution Impact Analysis
-- Aggregates metrics from Commits, Merge Requests, and Issues

CREATE OR REPLACE VIEW view_user_impact AS
SELECT 
    u.id as user_id,
    u.name as user_name,
    u.department as center_name,
    
    -- 1. Code Contribution
    COUNT(DISTINCT c.id) as commits_count,
    SUM(c.additions) as total_additions,
    SUM(c.deletions) as total_deletions,
    
    -- 2. Collaboration (Merge Requests)
    COUNT(DISTINCT mr.id) as total_mrs,
    SUM(CASE WHEN mr.state = 'merged' THEN 1 ELSE 0 END) as merged_mrs,
    SUM(CASE WHEN mr.state = 'opened' THEN 1 ELSE 0 END) as opened_mrs,
    
    -- 3. Issue Management
    COUNT(DISTINCT i.id) as total_issues_created,
    SUM(CASE WHEN i.state = 'closed' THEN 1 ELSE 0 END) as closed_issues_created,
    
    -- 4. Calculated Score (Example Weighting)
    -- Merged MR * 10 + Issue Created * 2 + Commit * 1
    (
        SUM(CASE WHEN mr.state = 'merged' THEN 1 ELSE 0 END) * 10 + 
        COUNT(DISTINCT i.id) * 2 +
        COUNT(DISTINCT c.id) * 1
    ) as contribution_score

FROM users u
-- Left Join Commits (via gitlab_user_id)
LEFT JOIN commits c ON u.id = c.gitlab_user_id
-- Left Join Merge Requests (via author_id)
LEFT JOIN merge_requests mr ON u.id = mr.author_id
-- Left Join Issues (via author_id)
LEFT JOIN issues i ON u.id = i.author_id

GROUP BY u.id, u.name, u.department
ORDER BY contribution_score DESC;

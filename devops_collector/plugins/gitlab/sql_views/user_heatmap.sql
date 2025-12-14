-- User Contribution Heatmap View
-- Aggregates daily activity for visualization (e.g. GitHub-style contribution graph)

CREATE OR REPLACE VIEW view_user_heatmap AS
SELECT 
    u.id as user_id,
    u.name as user_name,
    u.department as center,
    
    -- Time Dimension
    date_trunc('day', c.authored_date) as activity_date,
    
    -- Intensity Dimension
    COUNT(c.id) as commit_count,
    SUM(c.additions) as lines_added,
    SUM(c.deletions) as lines_deleted
    
FROM users u
JOIN commits c ON u.id = c.gitlab_user_id
GROUP BY 1, 2, 3, 4
ORDER BY 4 DESC;

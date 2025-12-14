-- User Lifecycle View
-- Identifies the first and last activity time for each user to analyze tenure and retention.

CREATE OR REPLACE VIEW view_user_lifecycle AS
SELECT 
    u.id as user_id,
    u.name as user_name,
    u.department,
    
    -- 1. First & Last Activity (Based on Commits)
    MIN(c.authored_date) as first_commit_at,
    MAX(c.authored_date) as last_commit_at,
    
    -- 2. Tenure / Active Duration (Days)
    -- PostgreSQL: EXTRACT(DAY FROM ...) or simple subtraction if date type
    -- SQLite: julianday()
    -- Universal approximation (Postgres specific here as we migrated):
    EXTRACT(DAY FROM (MAX(c.authored_date) - MIN(c.authored_date))) as active_days_count,
    
    -- 3. Retention Status
    CASE 
        WHEN MAX(c.authored_date) < CURRENT_DATE - INTERVAL '90 days' THEN 'Churned'
        WHEN MAX(c.authored_date) < CURRENT_DATE - INTERVAL '30 days' THEN 'Dormant'
        ELSE 'Active'
    END as status

FROM users u
JOIN commits c ON u.id = c.gitlab_user_id
GROUP BY u.id, u.name, u.department;

-- Project Value Analysis View
-- Aggregates Activity, Scale, and Quality metrics

CREATE OR REPLACE VIEW view_project_value AS
SELECT 
    p.id as project_id,
    p.name as project_name,
    p.department as center,
    
    -- 1. Activity Metrics
    p.last_activity_at,
    p.commit_count,
    p.updated_at,
    
    -- 2. Scale Metrics
    p.storage_size, -- In Bytes
    (p.storage_size / 1024 / 1024) as size_mb,
    
    -- 3. Structure & Quality
    p.branches_count,
    p.tags_count,
    
    -- 4. Collaboration Metrics
    COUNT(DISTINCT mr.id) as mr_count,
    SUM(CASE WHEN mr.state = 'merged' THEN 1 ELSE 0 END) as merged_mr_count,
    COUNT(DISTINCT i.id) as issue_count,
    
    -- 5. Effort Metrics (Time Tracking)
    SUM(i.total_time_spent) as total_hours_spent,
    
    -- 6. Activity Analysis (New)
    -- Recency: Days since last activity
    EXTRACT(DAY FROM (CURRENT_DATE - p.last_activity_at)) as days_since_last_activity,
    
    -- Activity Status: Active (<30d), Maintenance (<90d), Dormant (<365d), Archived (>365d)
    CASE 
        WHEN p.last_activity_at > CURRENT_DATE - INTERVAL '30 days' THEN 'Active'
        WHEN p.last_activity_at > CURRENT_DATE - INTERVAL '90 days' THEN 'Maintenance'
        WHEN p.last_activity_at > CURRENT_DATE - INTERVAL '365 days' THEN 'Dormant'
        ELSE 'Archived'
    END as activity_status,
    
    -- 7. VALUE INDEX (Refined Calculation)
    -- Base: Commit(0.1) + Tags(50) + Merged MRs(10)
    -- Bonus: Active Status
    (
        COALESCE(p.commit_count, 0) * 0.1 +
        COALESCE(p.tags_count, 0) * 50 +
        SUM(CASE WHEN mr.state = 'merged' THEN 1 ELSE 0 END) * 10 +
        (CASE 
            WHEN p.last_activity_at > CURRENT_DATE - INTERVAL '30 days' THEN 100 -- Active Bonus
            WHEN p.last_activity_at > CURRENT_DATE - INTERVAL '90 days' THEN 50  -- Maintenance Bonus
            ELSE 0 
        END)
    ) as value_score

FROM projects p
LEFT JOIN merge_requests mr ON p.id = mr.project_id
LEFT JOIN issues i ON p.id = i.project_id
GROUP BY p.id, p.name, p.department, p.last_activity_at, p.commit_count, p.storage_size, p.branches_count, p.tags_count;

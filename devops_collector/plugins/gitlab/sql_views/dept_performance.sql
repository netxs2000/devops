-- Department Performance Analysis (PMO View)
-- Aggregates metrics by Organization (Center/Department)

-- 1. Department Capacity & Scale
CREATE OR REPLACE VIEW view_dept_capacity AS
SELECT 
    o.id as org_id,
    o.name as org_name,
    COUNT(DISTINCT u.id) as headcount,
    COUNT(DISTINCT p.id) as project_count,
    SUM(p.storage_size) as total_asset_size,
    SUM(CASE WHEN p.last_activity_at > CURRENT_DATE - INTERVAL '30 days' THEN 1 ELSE 0 END) as active_project_count
FROM organizations o
LEFT JOIN users u ON o.id = u.organization_id
LEFT JOIN projects p ON o.id = p.organization_id
WHERE o.level IN ('Center', 'Department')
GROUP BY o.id, o.name;

-- 2. Department DORA Summary (Last 90 Days)
CREATE OR REPLACE VIEW view_dept_dora_summary AS
SELECT 
    o.id as org_id,
    o.name as org_name,
    
    -- Deployment Frequency: Total Deployments / Days / Projects (Rough Approx)
    COUNT(DISTINCT d.id) as total_deployments,
    
    -- Change Failure Rate
    (CAST(SUM(CASE WHEN d.status IN ('failed', 'canceled') THEN 1 ELSE 0 END) AS FLOAT) / 
     NULLIF(COUNT(DISTINCT d.id), 0)) * 100 as failure_rate,
     
    -- MTTR: Average time to close incidents (in Hours)
    AVG(
        EXTRACT(EPOCH FROM (i.closed_at - i.created_at)) / 3600.0
    ) as avg_mttr_hours

FROM organizations o
JOIN projects p ON o.id = p.organization_id
LEFT JOIN deployments d ON p.id = d.project_id AND d.created_at > CURRENT_DATE - INTERVAL '90 days'
LEFT JOIN issues i ON p.id = i.project_id 
    AND i.created_at > CURRENT_DATE - INTERVAL '90 days'
    -- Note: For JSONB use: AND i.labels @> '["incident"]' or similar. 
    -- Assuming text for broader compat or simple JSON check:
    AND CAST(i.labels AS TEXT) LIKE '%incident%'
WHERE o.level IN ('Center', 'Department')
GROUP BY o.id, o.name;

-- 3. Department Balanced Scorecard
CREATE OR REPLACE VIEW view_dept_scorecard AS
SELECT 
    c.org_name,
    c.headcount,
    c.project_count,
    c.active_project_count,
    
    -- Delivery Performance
    COALESCE(d.total_deployments, 0) as quarterly_deployments,
    ROUND(COALESCE(d.failure_rate, 0), 2) as failure_rate_pct,
    ROUND(COALESCE(d.avg_mttr_hours, 0), 1) as mttr_hours,
    
    -- Vitality (Active Projects / Total Projects)
    ROUND((CAST(c.active_project_count AS FLOAT) / NULLIF(c.project_count, 0)) * 100, 1) as vitality_score
    
FROM view_dept_capacity c
LEFT JOIN view_dept_dora_summary d ON c.org_id = d.org_id;

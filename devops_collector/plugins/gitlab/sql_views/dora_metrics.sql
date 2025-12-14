-- DORA Metrics Views
-- compatible with PostgreSQL

-- 1. Deployment Frequency
-- Count of successful deployments to production per day
CREATE OR REPLACE VIEW dora_deployment_frequency AS
SELECT 
    date_trunc('day', created_at) as deployment_date,
    project_id,
    count(*) as successful_deployments
FROM deployments
WHERE 
    status = 'success' 
    AND (environment LIKE '%prod%' OR environment LIKE '%production%')
GROUP BY 1, 2
ORDER BY 1 DESC;

-- 2. Lead Time for Changes
-- Time from commit authored date to deployment created date
-- Requires joining deployments -> project and commits -> project, but ideally direct link 
-- Here we approximate by linking the deployment SHA to the commit SHA
CREATE OR REPLACE VIEW dora_lead_time_for_changes AS
SELECT 
    d.project_id,
    d.id as deployment_id,
    c.id as commit_sha,
    d.created_at as deployed_at,
    c.authored_date as committed_at,
    EXTRACT(EPOCH FROM (d.created_at - c.authored_date)) as lead_time_seconds
FROM deployments d
JOIN commits c ON d.sha = c.id AND d.project_id = c.project_id
WHERE 
    d.status = 'success'
    AND (d.environment LIKE '%prod%' OR d.environment LIKE '%production%');

-- 3. Change Failure Rate
-- Percentage of deployments that caused a failure (e.g. status='failed')
-- Note: A more advanced version would link incidents to deployments
CREATE OR REPLACE VIEW dora_change_failure_rate AS
SELECT 
    project_id,
    count(*) as total_deployments,
    sum(CASE WHEN status = 'failed' OR status = 'canceled' THEN 1 ELSE 0 END) as failed_deployments,
    (sum(CASE WHEN status = 'failed' OR status = 'canceled' THEN 1 ELSE 0 END)::float / count(*)) * 100 as failure_rate_percentage
FROM deployments
WHERE 
    (environment LIKE '%prod%' OR environment LIKE '%production%')
GROUP BY project_id;

-- 4. Time to Restore Service (MTTR)
-- Average time to close issues labeled 'incident'
-- Note: Labels are stored as JSON, so we use jsonb operators if Postgres, or text logic if simplified
-- Assuming SQLite/Simple for now, matching text LIKE '%incident%' in labels string representation
-- For Postgres: WHERE labels::jsonb ? 'incident'
CREATE OR REPLACE VIEW dora_time_to_restore_service AS
SELECT 
    project_id,
    avg(EXTRACT(EPOCH FROM (closed_at - created_at))) as mttr_seconds,
    count(*) as incidents_count
FROM issues
WHERE 
    state = 'closed'
    AND closed_at IS NOT NULL
    AND labels::text LIKE '%incident%' -- Simplification for compatibility
GROUP BY project_id;

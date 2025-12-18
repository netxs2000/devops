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
    AND environment IN ('prod', 'production', 'prd', 'main') -- Standardized production environments
GROUP BY 1, 2
ORDER BY 1 DESC;

-- 2. Lead Time for Changes
-- Refined calculation: breakdown into coding, review, and deploy time
CREATE OR REPLACE VIEW dora_lead_time_for_changes AS
WITH mr_metrics AS (
    SELECT 
        mr.project_id,
        mr.iid as mr_iid,
        mr.merge_commit_sha,
        mr.created_at as mr_created_at,
        mr.merged_at as mr_merged_at,
        -- Find the first commit in this MR (simplified)
        (SELECT MIN(authored_date) FROM commits c WHERE c.project_id = mr.project_id AND c.id = mr.merge_commit_sha) as first_commit_at
    FROM merge_requests mr
    WHERE mr.state = 'merged' AND mr.merged_at IS NOT NULL
)
SELECT 
    d.project_id,
    d.id as deployment_id,
    m.mr_iid,
    d.created_at as deployed_at,
    m.first_commit_at,
    m.mr_created_at,
    m.mr_merged_at,
    -- Lead Time = Deploy Time - First Commit Authored Time
    EXTRACT(EPOCH FROM (d.created_at - m.first_commit_at)) as total_lead_time_seconds,
    -- Coding Time = MR Created - First Commit Authored
    EXTRACT(EPOCH FROM (m.mr_created_at - m.first_commit_at)) as coding_time_seconds,
    -- Review Time = MR Merged - MR Created
    EXTRACT(EPOCH FROM (m.mr_merged_at - m.mr_created_at)) as review_time_seconds,
    -- Deploy Time = Deployed At - MR Merged
    EXTRACT(EPOCH FROM (d.created_at - m.mr_merged_at)) as deploy_time_seconds
FROM deployments d
JOIN mr_metrics m ON d.sha = m.merge_commit_sha AND d.project_id = m.project_id
WHERE 
    d.status = 'success'
    AND d.environment IN ('prod', 'production', 'prd', 'main');

-- 3. Change Failure Rate
-- Percentage of deployments that caused a production incident
CREATE OR REPLACE VIEW dora_change_failure_rate AS
WITH prod_deployments AS (
    SELECT project_id, count(*) as total_count
    FROM deployments
    WHERE environment IN ('prod', 'production', 'prd', 'main')
    GROUP BY project_id
),
incidents AS (
    SELECT project_id, count(*) as incident_count
    FROM issues
    WHERE labels::text LIKE '%bug-source::production%'
    GROUP BY project_id
)
SELECT 
    pd.project_id,
    pd.total_count as total_deployments,
    COALESCE(i.incident_count, 0) as production_incidents,
    (COALESCE(i.incident_count, 0)::float / pd.total_count) * 100 as failure_rate_percentage
FROM prod_deployments pd
LEFT JOIN incidents i ON pd.project_id = i.project_id;

-- 4. Time to Restore Service (MTTR)
-- Average time to resolve 'bug-source::production' issues
CREATE OR REPLACE VIEW dora_time_to_restore_service AS
SELECT 
    project_id,
    avg(EXTRACT(EPOCH FROM (closed_at - created_at))) as mttr_seconds,
    count(*) as incidents_count
FROM issues
WHERE 
    state = 'closed'
    AND closed_at IS NOT NULL
    AND labels::text LIKE '%bug-source::production%'
GROUP BY project_id;

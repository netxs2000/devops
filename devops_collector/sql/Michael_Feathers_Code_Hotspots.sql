
-- View: view_file_hotspots
-- Purpose: Aggregates file-level statistics for Michael Feathers' Hotspot Analysis (Churn vs Complexity)
-- Logic:
--   1. Scope: Commits in the last 90 days (Dynamic Window).
--   2. Churn (Y-Axis): Count of distinct commits touching the file.
--   3. Complexity Proxy (X-Axis): Net code growth (Added - Deleted) as a rough LOC estimator.
--      Note: This is an estimation. Re-calibrating via full scan is better but expensive.

CREATE OR REPLACE VIEW view_file_hotspots AS
WITH file_stats AS (
    SELECT 
        cfs.file_path,
        cfs.commit_id,
        cfs.code_added,
        cfs.code_deleted,
        c.project_id,
        c.committed_date
    FROM 
        commit_file_stats cfs
    JOIN 
        commits c ON cfs.commit_id = c.id
    WHERE 
        cfs.file_path NOT LIKE '%.json' 
        AND cfs.file_path NOT LIKE '%.lock'
        AND cfs.file_path NOT LIKE '%.md'
        AND cfs.file_path NOT LIKE '%.txt'
        -- Filter out images/binaries roughly by extension or lack of code metrics
)
SELECT 
    f.project_id,
    f.file_path,
    
    -- Metric 1: Churn Frequency (Modifications in last 90 days)
    COUNT(DISTINCT CASE WHEN f.committed_date >= DATE('now', '-90 days') THEN f.commit_id END) as churn_90d,
    
    -- Metric 2: Complexity Proxy (Net Lines of Code Accumulated)
    -- We sum all history available to guess size. 
    -- ABS is used to prevent negative artifacts if history is partial.
    ABS(SUM(f.code_added) - SUM(f.code_deleted)) as estimated_loc,
    
    -- Context
    MAX(f.committed_date) as last_modified_at,
    COUNT(DISTINCT CASE WHEN f.committed_date >= DATE('now', '-90 days') THEN f.commit_id END) * 
    LOG(ABS(SUM(f.code_added) - SUM(f.code_deleted)) + 2) as risk_factor -- Proprietary Risk Score
    
FROM 
    file_stats f
GROUP BY 
    f.project_id, f.file_path
HAVING 
    churn_90d > 0 -- Only show active files
    AND estimated_loc > 10 -- Ignore tiny files
ORDER BY 
    risk_factor DESC;

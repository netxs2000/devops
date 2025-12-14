-- Activity Analysis Views
-- Provides data for various activity charts and heatmaps

-- ===========================================
-- 1. Hour of Week Heatmap
-- X-axis: Hour (0-23), Y-axis: Day of Week (Mon-Sun)
-- Value: Commit Count
-- ===========================================
CREATE OR REPLACE VIEW view_activity_hour_of_week AS
SELECT
    p.id as project_id,
    p.name as project_name,
    CASE EXTRACT(DOW FROM c.committed_date)
        WHEN 0 THEN 'Sun'
        WHEN 1 THEN 'Mon'
        WHEN 2 THEN 'Tue'
        WHEN 3 THEN 'Wed'
        WHEN 4 THEN 'Thu'
        WHEN 5 THEN 'Fri'
        WHEN 6 THEN 'Sat'
    END as weekday,
    EXTRACT(DOW FROM c.committed_date)::int as weekday_num,  -- 0=Sun for sorting
    EXTRACT(HOUR FROM c.committed_date)::int as hour,
    COUNT(*) as commit_count
FROM commits c
JOIN projects p ON c.project_id = p.id
GROUP BY p.id, p.name, EXTRACT(DOW FROM c.committed_date), EXTRACT(HOUR FROM c.committed_date)
ORDER BY weekday_num, hour;

-- ===========================================
-- 2. Yearly Activity (Last 20 years)
-- X-axis: Year, Y-axis: Commit Count
-- ===========================================
CREATE OR REPLACE VIEW view_activity_yearly AS
SELECT
    p.id as project_id,
    p.name as project_name,
    EXTRACT(YEAR FROM c.committed_date)::int as year,
    COUNT(*) as commit_count
FROM commits c
JOIN projects p ON c.project_id = p.id
WHERE c.committed_date >= NOW() - INTERVAL '20 years'
GROUP BY p.id, p.name, EXTRACT(YEAR FROM c.committed_date)
ORDER BY year;

-- ===========================================
-- 3. Weekly Activity (Last 32 weeks)
-- X-axis: Week Number (relative), Y-axis: Commit Count
-- ===========================================
CREATE OR REPLACE VIEW view_activity_weekly AS
SELECT
    p.id as project_id,
    p.name as project_name,
    -- Calculate relative week number (1 = current week, 32 = 32 weeks ago)
    EXTRACT(WEEK FROM NOW())::int - EXTRACT(WEEK FROM c.committed_date)::int + 
        (EXTRACT(YEAR FROM NOW())::int - EXTRACT(YEAR FROM c.committed_date)::int) * 52 as weeks_ago,
    DATE_TRUNC('week', c.committed_date) as week_start,
    COUNT(*) as commit_count
FROM commits c
JOIN projects p ON c.project_id = p.id
WHERE c.committed_date >= NOW() - INTERVAL '32 weeks'
GROUP BY p.id, p.name, DATE_TRUNC('week', c.committed_date), weeks_ago
ORDER BY weeks_ago DESC;

-- ===========================================
-- 4. Hour of Day Activity (Table & Bar Chart)
-- X-axis: Hour (0-23), Y-axis: Commit Count & Percentage
-- ===========================================
CREATE OR REPLACE VIEW view_activity_hour_of_day AS
WITH hourly_counts AS (
    SELECT
        p.id as project_id,
        p.name as project_name,
        EXTRACT(HOUR FROM c.committed_date)::int as hour,
        COUNT(*) as commit_count
    FROM commits c
    JOIN projects p ON c.project_id = p.id
    GROUP BY p.id, p.name, EXTRACT(HOUR FROM c.committed_date)
),
project_totals AS (
    SELECT project_id, SUM(commit_count) as total_commits
    FROM hourly_counts
    GROUP BY project_id
)
SELECT
    hc.project_id,
    hc.project_name,
    hc.hour,
    hc.commit_count,
    ROUND((hc.commit_count::decimal / pt.total_commits) * 100, 2) as percentage
FROM hourly_counts hc
JOIN project_totals pt ON hc.project_id = pt.project_id
ORDER BY hc.project_id, hc.hour;

-- ===========================================
-- 5. Global Activity Summary (All Projects Combined)
-- For organization-wide dashboards
-- ===========================================
CREATE OR REPLACE VIEW view_activity_global_hour_of_week AS
SELECT
    CASE EXTRACT(DOW FROM c.committed_date)
        WHEN 0 THEN 'Sun'
        WHEN 1 THEN 'Mon'
        WHEN 2 THEN 'Tue'
        WHEN 3 THEN 'Wed'
        WHEN 4 THEN 'Thu'
        WHEN 5 THEN 'Fri'
        WHEN 6 THEN 'Sat'
    END as weekday,
    EXTRACT(DOW FROM c.committed_date)::int as weekday_num,
    EXTRACT(HOUR FROM c.committed_date)::int as hour,
    COUNT(*) as commit_count
FROM commits c
GROUP BY EXTRACT(DOW FROM c.committed_date), EXTRACT(HOUR FROM c.committed_date)
ORDER BY weekday_num, hour;

CREATE OR REPLACE VIEW view_activity_global_yearly AS
SELECT
    EXTRACT(YEAR FROM c.committed_date)::int as year,
    COUNT(*) as commit_count
FROM commits c
WHERE c.committed_date >= NOW() - INTERVAL '20 years'
GROUP BY EXTRACT(YEAR FROM c.committed_date)
ORDER BY year;

CREATE OR REPLACE VIEW view_activity_global_hour_of_day AS
WITH hourly_counts AS (
    SELECT
        EXTRACT(HOUR FROM c.committed_date)::int as hour,
        COUNT(*) as commit_count
    FROM commits c
    GROUP BY EXTRACT(HOUR FROM c.committed_date)
),
total_commits AS (
    SELECT SUM(commit_count) as total FROM hourly_counts
)
SELECT
    hc.hour,
    hc.commit_count,
    ROUND((hc.commit_count::decimal / tc.total) * 100, 2) as percentage
FROM hourly_counts hc, total_commits tc
ORDER BY hc.hour;

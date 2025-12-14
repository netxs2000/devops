-- Tag Analytics View
-- Approximates the "Release Content" by associating commits with the nearest preceding tag.
-- 
-- Logic:
-- 1. Order tags by creation date.
-- 2. Define "Release Window" for a tag as (Previous Tag Date, Current Tag Date].
-- 3. Count commits and authors within that window.

CREATE OR REPLACE VIEW view_tag_analytics AS
WITH tag_windows AS (
    SELECT 
        t.project_id,
        t.name as tag_name,
        t.created_at as tag_date,
        LAG(t.created_at) OVER (PARTITION BY t.project_id ORDER BY t.created_at) as prev_tag_date
    FROM tags t
),
tag_stats AS (
    SELECT 
        tw.project_id,
        tw.tag_name,
        tw.tag_date,
        COUNT(c.id) as commit_count,
        COUNT(DISTINCT c.author_name) as author_count,
        STRING_AGG(DISTINCT c.author_name, ', ') as author_list
    FROM tag_windows tw
    LEFT JOIN commits c ON c.project_id = tw.project_id 
        AND c.committed_date <= tw.tag_date 
        AND (tw.prev_tag_date IS NULL OR c.committed_date > tw.prev_tag_date)
    GROUP BY tw.project_id, tw.tag_name, tw.tag_date
)
SELECT
    p.name as project_name,
    ts.tag_name,
    ts.tag_date,
    ts.commit_count,
    ts.author_list
FROM tag_stats ts
JOIN projects p ON ts.project_id = p.id
ORDER BY ts.tag_date DESC;

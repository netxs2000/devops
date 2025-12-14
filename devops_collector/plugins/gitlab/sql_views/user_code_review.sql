-- User Code Review Impact View
-- Analyzes code review behaviors by counting comments on Merge Requests.
-- Filters out system notes and self-reviews to capture true peer review impact.

CREATE OR REPLACE VIEW view_user_code_review AS
SELECT 
    u.id as user_id,
    u.name as user_name,
    u.department,
    
    -- 1. Review Breadth (Number of MRs reviewed)
    -- Count MRs where user left a comment but was NOT the author
    COUNT(DISTINCT mr.id) as mrs_reviewed_count,
    
    -- 2. Review Depth (Total Comments)
    COUNT(n.id) as total_review_comments,
    
    -- 3. Average Interaction
    CASE 
        WHEN COUNT(DISTINCT mr.id) > 0 THEN 
            ROUND(CAST(COUNT(n.id) AS FLOAT) / COUNT(DISTINCT mr.id), 1)
        ELSE 0 
    END as avg_comments_per_review

FROM users u
JOIN notes n ON u.id = n.author_id
JOIN merge_requests mr ON n.noteable_iid = mr.iid AND n.project_id = mr.project_id
WHERE n.noteable_type = 'MergeRequest'
  AND n.system = FALSE -- Exclude system events (e.g. "assigned to", "changed label")
  AND mr.author_id != u.id -- Exclude self-comments
GROUP BY u.id, u.name, u.department
ORDER BY total_review_comments DESC;

-- User Tech Stack Breadth View
-- Analyzes the programming languages used by each user based on file extensions in their commits.

CREATE OR REPLACE VIEW view_user_tech_stack AS
SELECT 
    u.id as user_id,
    u.name as user_name,
    u.department,
    
    -- 1. Tech Width (Number of Languages Used)
    COUNT(DISTINCT cfs.language) as language_count,
    
    -- 2. Tech Depth (Total Lines Added)
    SUM(cfs.code_added) as total_code_added,
    
    -- 3. Skill Tree (Comma-separated list of languages)
    STRING_AGG(DISTINCT cfs.language, ', ') as skills_list

FROM users u
JOIN commits c ON u.id = c.gitlab_user_id
JOIN commit_file_stats cfs ON c.id = cfs.commit_id
WHERE cfs.language IS NOT NULL 
  AND cfs.language != 'unknown'
GROUP BY u.id, u.name, u.department
ORDER BY language_count DESC;

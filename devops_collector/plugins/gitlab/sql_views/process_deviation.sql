-- 3.13 隐性工作与流程偏离 (Process Deviation)

-- 指标1: 游离代码率 (Unmanaged Code Ratio)
-- 定义: Message 中不包含 Jira/Issue ID 模式 (如 PROJ-123 或 #123) 的 Commit 占比
CREATE OR REPLACE VIEW view_process_deviation_unmanaged AS
SELECT 
    p.name AS project_name,
    COUNT(*) AS total_commits,
    -- 简单正则匹配: 匹配 #数字 或 2-10个大写字母-数字
    COUNT(CASE WHEN c.title !~ '(#\d+|[A-Z]{2,10}-\d+)' THEN 1 END) AS unmanaged_commits,
    ROUND(
        COUNT(CASE WHEN c.title !~ '(#\d+|[A-Z]{2,10}-\d+)' THEN 1 END) * 100.0 / COUNT(*), 
        2
    ) AS unmanaged_ratio
FROM 
    commits c
JOIN 
    projects p ON c.project_id = p.id
WHERE 
    c.committed_date > NOW() - INTERVAL '90 days'
GROUP BY 
    p.name
ORDER BY 
    unmanaged_ratio DESC;


-- 指标2: 幽灵分支 (Ghost Branches)
-- 定义: 30天无提交，且未合并，且不在保护分支列表(main, master, dev)中
CREATE OR REPLACE VIEW view_process_ghost_branches AS
SELECT 
    p.name AS project_name,
    b.name AS branch_name,
    b.last_commit_date,
    current_date - DATE(b.last_commit_date) AS inactive_days,
    u.name AS last_committer
-- 需要 branches 表支持 last_commit_date 等字段，假设已采集
FROM 
    branches b
JOIN 
    projects p ON b.project_id = p.id
LEFT JOIN
    users u ON b.last_committer_email = u.email 
WHERE 
    b.name NOT IN ('main', 'master', 'develop', 'dev', 'production')
    AND b.is_merged = FALSE
    AND b.last_commit_date < NOW() - INTERVAL '30 days'
ORDER BY 
    inactive_days DESC;

-- 3.15 跨边界协作力 (InnerSource Impact)

-- 指标1: 内源贡献率 (InnerSource Rate)
-- 定义: 用户 Push 代码到非自己所属部门的项目
-- 前提: users 表和 projects 表都有 organization_id 或 department 字段
CREATE OR REPLACE VIEW view_innersource_rate AS
SELECT 
    u.name AS user_name,
    u.department AS user_dept,
    COUNT(c.id) AS total_commits,
    -- 跨部门提交数
    COUNT(CASE WHEN p.department != u.department THEN 1 END) AS cross_dept_commits,
    ROUND(
        COUNT(CASE WHEN p.department != u.department THEN 1 END) * 100.0 / COUNT(c.id), 
        2
    ) AS innersource_ratio
FROM 
    commits c
JOIN 
    users u ON c.gitlab_user_id = u.id -- 使用内部ID关联
JOIN 
    projects p ON c.project_id = p.id
WHERE 
    u.department IS NOT NULL AND p.department IS NOT NULL
GROUP BY 
    u.name, u.department
HAVING 
    COUNT(c.id) > 10
ORDER BY 
    innersource_ratio DESC;


-- 指标2: 知识孤岛指数 (Silo Index / Bus Factor Risk)
-- 定义: 某个文件 80% 以上的代码行数(或提交次数)都来自同一个人
-- 这里用提交次数简算
CREATE OR REPLACE VIEW view_silo_risk_files AS
WITH file_authors AS (
    SELECT 
        fs.file_path,
        c.author_email,
        COUNT(*) AS commit_count
    FROM 
        commit_file_stats fs
    JOIN 
        commits c ON fs.commit_id = c.id
    GROUP BY 
        fs.file_path, c.author_email
),
file_total AS (
    SELECT 
        file_path,
        SUM(commit_count) AS total_commits
    FROM 
        file_authors
    GROUP BY 
        file_path
)
SELECT 
    fa.file_path,
    fa.author_email AS dominant_author,
    fa.commit_count,
    ft.total_commits,
    ROUND(fa.commit_count * 100.0 / ft.total_commits, 2) AS ownership_ratio
FROM 
    file_authors fa
JOIN 
    file_total ft ON fa.file_path = ft.file_path
WHERE 
    ft.total_commits > 5 -- 忽略刚建立的文件
    AND (fa.commit_count * 1.0 / ft.total_commits) > 0.8 -- 超过 80% 由一人完成
ORDER BY 
    ft.total_commits DESC, ownership_ratio DESC;

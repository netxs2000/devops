-- 3.14 代码演进与架构熵 (Code Evolution)

-- 指标1: 重构比率 (Refactoring Ratio)
-- 核心逻辑: 删除行数 / 新增行数 的比值。
-- > 0.8 且 < 1.2 可视为重构 (替换逻辑)； > 5 视为大面积删除废弃代码。
CREATE OR REPLACE VIEW view_code_evolution_refactoring AS
SELECT 
    p.name AS project_name,
    DATE_TRUNC('month', c.committed_date) AS month,
    SUM(c.additions) AS total_additions,
    SUM(c.deletions) AS total_deletions,
    CASE 
        WHEN SUM(c.additions) = 0 THEN 0 
        ELSE ROUND(SUM(c.deletions)::numeric / SUM(c.additions), 2) 
    END AS refactoring_index,
    CASE 
        WHEN SUM(c.additions) = 0 THEN 'Maintenance'
        WHEN (SUM(c.deletions)::numeric / SUM(c.additions)) BETWEEN 0.8 AND 1.2 THEN 'Refactoring'
        WHEN (SUM(c.deletions)::numeric / SUM(c.additions)) < 0.3 THEN 'New Features'
        ELSE 'Mixed'
    END AS work_type
FROM 
    commits c
JOIN 
    projects p ON c.project_id = p.id
WHERE 
    c.committed_date > NOW() - INTERVAL '12 months'
GROUP BY 
    p.name, 2
ORDER BY 
    p.name, month;


-- 指标2: 逻辑耦合热度 (Logical Coupling / Co-Change)
-- 核心逻辑: 统计哪些顶层目录(Top-level directories)经常在同一个 Commit 中一起变化
-- 前提: 必须有 commit_file_stats 表记录每个 commit 的文件
CREATE OR REPLACE VIEW view_logical_coupling AS
WITH file_changes AS (
    SELECT 
        commit_id,
        -- 提取一级目录，例如 src/main.py -> src
        SPLIT_PART(file_path, '/', 1) AS root_module
    FROM 
        commit_file_stats
    GROUP BY 
        commit_id, 2 -- 去重，同一个commit里若改了 src/a.py 和 src/b.py，只算 src 改了一次
),
co_changes AS (
    SELECT 
        a.root_module AS module_a,
        b.root_module AS module_b,
        COUNT(*) AS co_change_count
    FROM 
        file_changes a
    JOIN 
        file_changes b ON a.commit_id = b.commit_id AND a.root_module < b.root_module
    GROUP BY 
        1, 2
)
SELECT 
    module_a,
    module_b,
    co_change_count
FROM 
    co_changes
WHERE 
    co_change_count > 5 -- 过滤掉偶然的耦合
ORDER BY 
    co_change_count DESC;

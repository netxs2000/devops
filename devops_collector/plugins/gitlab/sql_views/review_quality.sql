-- 3.11 协作熵与评审质量 (Review Quality & Democracy)

-- 指标1: 评审乒乓指数 (Ping-Pong Index)
-- 定义: MR 先后被不同人评论和修改的轮次。这里简化为评论总数，因为每次互动都代表一次"乒乓"。
-- 更精准的逻辑需要分析 System Note 中的 "added x commits" 和 "commented" 的交替时间戳，这里用 note count 估算。
CREATE OR REPLACE VIEW view_review_ping_pong_index AS
WITH mr_stats AS (
    SELECT 
        mr.project_id,
        mr.id AS mr_id,
        mr.iid AS mr_iid,
        mr.title,
        mr.author_id,
        COUNT(CASE WHEN n.system = FALSE THEN 1 END) AS interaction_count,
        COUNT(DISTINCT n.author_id) AS reviewer_count
    FROM 
        merge_requests mr
    LEFT JOIN 
        notes n ON mr.id = n.noteable_id AND n.noteable_type = 'MergeRequest'
    WHERE 
        mr.state = 'merged'
    GROUP BY 
        mr.project_id, mr.id, mr.iid, mr.title, mr.author_id
)
SELECT 
    p.name AS project_name,
    ms.mr_iid,
    ms.title,
    u.name AS author_name,
    ms.interaction_count AS ping_pong_rounds,
    ms.reviewer_count,
    CASE 
        WHEN ms.interaction_count = 0 THEN 'Rubber Stamp (橡皮图章)'
        WHEN ms.interaction_count BETWEEN 1 AND 5 THEN 'Healthy'
        ELSE 'Bike-shedding (过度纠结)'
    END AS review_quality_label
FROM 
    mr_stats ms
JOIN 
    projects p ON ms.project_id = p.id
LEFT JOIN 
    users u ON ms.author_id = u.id;


-- 指标2: 评审民主度 (Review Democracy)
-- 定义: 统计每个项目中，谁在执行 "Merge" 操作（通常 System Note 中会有 "merged" 记录，或直接取 merged_by_id 如果采集了的话）
-- 假设 Data Dictionary 中 MR 表可能有 merged_by_id，如果没有，暂且无法精准统计，这里假设我们后续会采集 merged_by_id。
-- 如果没有该字段，可以统计 "Who commented last before merge"。
-- 现阶段用“参与过评审的人数分布”来近似。
CREATE OR REPLACE VIEW view_review_democracy AS
SELECT 
    p.name AS project_name,
    COUNT(DISTINCT n.author_id) AS total_unique_reviewers,
    -- 基尼系数概念的简化版：头部评审人占比
    (
        SELECT COUNT(DISTINCT top_reviewers.author_id)
        FROM (
            SELECT author_id 
            FROM notes n2 
            WHERE n2.project_id = p.id AND n2.noteable_type = 'MergeRequest'
            GROUP BY author_id 
            ORDER BY COUNT(*) DESC 
            LIMIT 3
        ) top_reviewers
    ) AS top3_reviewers_count,
    -- 只是一个示意，实际应用需要更复杂的基尼系数计算
    'Consult Detail Report' as distribution_status
FROM 
    projects p
LEFT JOIN 
    notes n ON p.id = n.project_id AND n.noteable_type = 'MergeRequest' AND n.system = FALSE
GROUP BY 
    p.id, p.name;

-- 3.12 团队倦怠雷达 (Burnout Radar)

-- 指标1: WLB 指数 (Work-Life Balance)
-- 假设数据库时区为 UTC，需调整为本地时间 (此处示例 +8)
-- 工作时间定义: 周一到周五, 09:00 - 19:00
CREATE OR REPLACE VIEW view_burnout_wlb_index AS
WITH all_commits AS (
    SELECT 
        c.id,
        c.author_email,
        c.committed_date,
        -- 转换为本地时间 (假设 +8 区)
        c.committed_date + INTERVAL '8 hours' AS local_time,
        EXTRACT(DOW FROM (c.committed_date + INTERVAL '8 hours')) AS dow, -- 0=Sun, 6=Sat
        EXTRACT(HOUR FROM (c.committed_date + INTERVAL '8 hours')) AS hour_of_day
    FROM 
        commits c
    WHERE 
        c.committed_date > NOW() - INTERVAL '90 days'
)
SELECT 
    u.name AS user_name,
    u.email,
    COUNT(*) AS total_commits,
    -- 周末提交
    COUNT(CASE WHEN dow IN (0, 6) THEN 1 END) AS weekend_commits,
    -- 深夜提交 (19:00 - 09:00)
    COUNT(CASE WHEN hour_of_day < 9 OR hour_of_day >= 19 THEN 1 END) AS off_hours_commits,
    -- WLB 异常率 = (周末 + 深夜) / 总提交 (去重，因为周末也是深夜的情况需要考虑，简单起见相加)
    -- 更严谨写法：CASE WHEN (dow IN (0,6)) OR (hour <9 OR hour>=19) THEN 1
    ROUND(
        COUNT(CASE WHEN (dow IN (0, 6)) OR (hour_of_day < 9 OR hour_of_day >= 19) THEN 1 END) * 100.0 / COUNT(*), 
        2
    ) AS burnout_risk_score
FROM 
    all_commits ac
JOIN 
    users u ON ac.author_email = u.email -- 这里假设 email 已归一化
GROUP BY 
    u.name, u.email
HAVING 
    COUNT(*) > 10 -- 忽略极低频贡献者
ORDER BY 
    burnout_risk_score DESC;


-- 指标2: 冲刺后遗症 (Post-Crunch Quality Dip)
-- 核心逻辑: 比较 "发布日(Tag Date)" 之后 7 天内的 Bug Issue 创建率
-- 需要 tags 表和 issues 表配合
CREATE OR REPLACE VIEW view_post_crunch_dip AS
SELECT 
    p.name AS project_name,
    t.name AS tag_name,
    t.commit_date AS release_date,
    -- 统计该 Tag 发布后 7 天内创建的 label 包含 'bug' 的 Issue 数量
    (
        SELECT COUNT(*)
        FROM issues i
        WHERE i.project_id = p.id
          AND i.created_at BETWEEN t.commit_date AND (t.commit_date + INTERVAL '7 days')
          -- 假设 labels 存储为 JSONB 或数组，这里用文本模糊匹配示例
          AND i.labels::text LIKE '%bug%'
    ) AS post_release_bugs,
    -- 对比平时周均 Bug 数 (简化逻辑: 取发布前 30 天的总数 / 4)
    ROUND(
        (
            SELECT COUNT(*)
            FROM issues i2
            WHERE i2.project_id = p.id
              AND i2.created_at BETWEEN (t.commit_date - INTERVAL '30 days') AND t.commit_date
              AND i2.labels::text LIKE '%bug%'
        ) / 4.0, 
        2
    ) AS avg_weekly_bugs_before
FROM 
    tags t
JOIN 
    projects p ON t.project_id = p.id
WHERE 
    t.commit_date > NOW() - INTERVAL '180 days'
ORDER BY 
    t.commit_date DESC;

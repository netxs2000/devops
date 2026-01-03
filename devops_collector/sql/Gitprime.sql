-- GitPrime Style Engineering Metrics View
-- GitPrime 风格的研发效能看板视图
-- 包含核心指标：ELOC, Impact (影响), Churn (反复/代码流失), Active Days (活跃天数)

CREATE OR REPLACE VIEW view_gitprime_metrics AS
WITH user_metrics AS (
    -- 1. 聚合提交相关的核心指标
    SELECT 
        u.global_user_id,
        u.full_name,
        u.primary_email,
        u.department_id,
        COUNT(DISTINCT cm.commit_id) as total_commits,
        COUNT(DISTINCT DATE(cm.committed_at)) as active_days,
        SUM(cm.eloc_score) as total_eloc,
        SUM(cm.impact_score) as total_impact,
        SUM(cm.churn_lines) as total_churn,
        SUM(cm.raw_additions) as raw_additions,
        SUM(cm.raw_deletions) as raw_deletions,
        SUM(cm.comment_lines) as total_comments,
        SUM(cm.test_lines) as total_tests,
        AVG(cm.refactor_ratio) as avg_refactor_ratio
    FROM mdm_identities u
    JOIN commit_metrics cm ON u.primary_email = cm.author_email
    WHERE cm.committed_at >= DATE('now', '-90 days') -- 最近90天
    GROUP BY u.global_user_id, u.full_name, u.primary_email, u.department_id
),
rankings AS (
    -- 2. 计算派生指标与排名
    SELECT 
        *,
        DENSE_RANK() OVER (ORDER BY total_impact DESC) as rank_position, -- 以 Impact 排名更能体现价值
        CASE 
            WHEN raw_additions > 0 THEN ROUND((total_churn * 100.0 / raw_additions), 1)
            ELSE 0 
        END as churn_rate_percent
    FROM user_metrics
)
SELECT 
    rank_position,
    full_name,
    department_id,
    active_days,
    total_commits as commits_90d,
    ROUND(total_eloc, 1) as eloc_score,
    ROUND(total_impact, 1) as impact_score,
    churn_rate_percent as "churn_rate%",
    ROUND((avg_refactor_ratio * 100), 1) as "refactor_intensity%",
    CASE 
        WHEN rank_position <= 3 THEN 'Elite'
        WHEN rank_position <= 10 THEN 'Core'
        WHEN rank_position <= 30 THEN 'Contributor'
        ELSE 'Member'
    END as contributor_level
FROM rankings
ORDER BY impact_score DESC;

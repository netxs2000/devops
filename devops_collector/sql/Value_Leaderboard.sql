-- Value Contribution Leaderboard View
-- 价值贡献排行榜视图
-- 统计每个开发者的累计代码当量 (ELOC) 及其在团队中的排名，
-- 同时展示其代码构成特征（注释率、测试率、重构率）。

CREATE OR REPLACE VIEW view_leaderboard_value_contribution AS
WITH user_metrics AS (
    -- 1. 聚合每个用户的提交指标
    SELECT 
        u.global_user_id,
        u.full_name,
        u.primary_email,
        u.department_id,
        COUNT(DISTINCT cm.commit_id) as total_commits,
        SUM(cm.eloc_score) as total_eloc,
        SUM(cm.raw_additions) as raw_additions,
        SUM(cm.raw_deletions) as raw_deletions,
        SUM(cm.comment_lines) as total_comments,
        SUM(cm.test_lines) as total_tests,
        AVG(cm.refactor_ratio) as avg_refactor_ratio
    FROM mdm_identities u
    JOIN commit_metrics cm ON u.primary_email = cm.author_email
    WHERE cm.committed_at >= NOW() - INTERVAL '90 days' -- 仅统计最近90天，保持活跃度
    GROUP BY u.global_user_id, u.full_name, u.primary_email, u.department_id
),
rankings AS (
    -- 2. 计算排名与比率
    SELECT 
        *,
        DENSE_RANK() OVER (ORDER BY total_eloc DESC) as rank_position,
        ROUND((total_comments::DECIMAL / NULLIF(raw_additions, 0) * 100), 1) as comment_ratio_percent,
        ROUND((total_tests::DECIMAL / NULLIF(raw_additions, 0) * 100), 1) as test_ratio_percent
    FROM user_metrics
)
SELECT 
    rank_position,
    full_name,
    department_id,
    ROUND(total_eloc::NUMERIC, 1) as eloc_score,
    total_commits as commits_90d,
    test_ratio_percent as "test_coverage_rate%",
    comment_ratio_percent as "doc_contribution_rate%",
    ROUND((avg_refactor_ratio * 100)::NUMERIC, 1) as "refactor_intensity%",
    CASE 
        WHEN rank_position <= 3 THEN 'Elite'
        WHEN rank_position <= 10 THEN 'Core'
        WHEN rank_position <= 30 THEN 'Contributor'
        ELSE 'Member'
    END as contributor_level
FROM rankings
ORDER BY total_eloc DESC;

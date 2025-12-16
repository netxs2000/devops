-- ============================================================
-- HR Analytics Views for DevOps
-- 此脚本用于创建人力资源视角的数据分析视图
-- 包含：能力画像、技术栈分布、流失风险预警、个人质量计分卡
-- ============================================================

-- 1. 人员能力综合画像 (User Capability Profile)
-- 用途：绘制雷达图 (Radar Chart)
-- 维度：产出(Commits), 影响(Merged MRs), 协作(Reviews), 质量(Bugs), 投入(Active Days)
CREATE OR REPLACE VIEW view_hr_user_capability_profile AS
WITH user_commits AS (
    SELECT 
        gitlab_user_id,
        COUNT(*) as commit_count,
        SUM(additions) as total_additions,
        COUNT(DISTINCT DATE(committed_date)) as active_days
    FROM commits
    WHERE committed_date >= NOW() - INTERVAL '90 days'
    GROUP BY gitlab_user_id
),
mr_activity AS (
    SELECT 
        author_id,
        COUNT(*) as mr_created,
        SUM(CASE WHEN state = 'merged' THEN 1 ELSE 0 END) as mr_merged
    FROM merge_requests
    WHERE created_at >= NOW() - INTERVAL '90 days'
    GROUP BY author_id
),
review_activity AS (
    SELECT 
        author_id,
        COUNT(*) as comments_made,
        COUNT(DISTINCT noteable_iid) as issues_mrs_touched
    FROM notes
    WHERE created_at >= NOW() - INTERVAL '90 days'
    AND system = false 
    GROUP BY author_id
),
quality_metric AS (
    SELECT 
        author,
        COUNT(*) as total_issues,
        SUM(CASE WHEN severity IN ('BLOCKER', 'CRITICAL') THEN 1 ELSE 0 END) as critical_issues
    FROM sonar_issues
    WHERE creation_date >= NOW() - INTERVAL '90 days'
    GROUP BY author
)
SELECT 
    u.id as user_id,
    u.name,
    u.department,
    o.name as group_name,
    
    COALESCE(uc.commit_count, 0) as metric_commits,
    COALESCE(uc.total_additions, 0) as metric_code_lines,
    COALESCE(ma.mr_merged, 0) as metric_mr_merged,
    COALESCE(ra.comments_made, 0) as metric_reviews_comments,
    COALESCE(qm.critical_issues, 0) as metric_critical_bugs,
    COALESCE(uc.active_days, 0) as metric_active_days

FROM users u
LEFT JOIN organizations o ON u.organization_id = o.id
LEFT JOIN user_commits uc ON u.id = uc.gitlab_user_id
LEFT JOIN mr_activity ma ON u.id = ma.author_id
LEFT JOIN review_activity ra ON u.id = ra.author_id
LEFT JOIN quality_metric qm ON u.username = qm.author
WHERE u.state = 'active' AND u.is_virtual = false;


-- 2. 技术栈分布 (Tech Stack Radar)
-- 用途：识别技术专家和团队技能短板
CREATE OR REPLACE VIEW view_hr_user_tech_stack AS
SELECT 
    u.name as user_name,
    u.department,
    cfs.language,
    SUM(cfs.code_added) as lines_added,
    COUNT(distinct c.project_id) as projects_involved,
    MAX(c.committed_date) as last_used_at
FROM commit_file_stats cfs
JOIN commits c ON cfs.commit_id = c.id
JOIN users u ON c.gitlab_user_id = u.id
WHERE c.committed_date >= NOW() - INTERVAL '180 days'
AND cfs.language IS NOT NULL
AND cfs.language NOT IN ('json', 'yaml', 'md', 'txt', 'xml')
GROUP BY u.name, u.department, cfs.language
ORDER BY u.name, lines_added DESC;


-- 3. 人才流失风险预警 (Churn Risk Dashboard)
-- 用途：识别加班严重 (Burnout) 或 活跃度断崖 (Disengaged) 的员工
CREATE OR REPLACE VIEW view_hr_retention_risk AS
WITH monthly_stats AS (
    SELECT 
        gitlab_user_id,
        TO_CHAR(committed_date, 'YYYY-MM') as month_str,
        COUNT(*) as commit_count,
        SUM(CASE 
            WHEN EXTRACT(HOUR FROM committed_date) >= 22 OR EXTRACT(HOUR FROM committed_date) < 6 
            THEN 1 ELSE 0 
        END) as late_night_commits,
        SUM(CASE 
            WHEN EXTRACT(ISODOW FROM committed_date) IN (6, 7) 
            THEN 1 ELSE 0 
        END) as weekend_commits
    FROM commits
    WHERE committed_date >= NOW() - INTERVAL '4 months'
    GROUP BY gitlab_user_id, TO_CHAR(committed_date, 'YYYY-MM')
)
SELECT 
    u.name,
    u.department,
    curr.month_str as current_month,
    curr.commit_count,
    
    -- Burnout Risk (Overtime %)
    ROUND((curr.late_night_commits + curr.weekend_commits)::numeric / NULLIF(curr.commit_count, 0) * 100, 1) as overtime_ratio_pct,
    CASE 
        WHEN (curr.late_night_commits + curr.weekend_commits)::numeric / NULLIF(curr.commit_count, 0) > 0.3 THEN 'HIGH_BURNOUT'
        ELSE 'NORMAL'
    END as burnout_risk_level,
    
    -- Disengagement Risk (MoM Drop)
    prev.commit_count as prev_month_commit,
    ROUND((curr.commit_count - prev.commit_count)::numeric / NULLIF(prev.commit_count, 0) * 100, 1) as mom_change_pct,
    CASE 
        WHEN prev.commit_count > 10 AND curr.commit_count < (prev.commit_count * 0.2) THEN 'HIGH_DROP_OFF'
        WHEN prev.commit_count > 10 AND curr.commit_count < (prev.commit_count * 0.5) THEN 'MEDIUM_DROP_OFF'
        ELSE 'STABLE'
    END as retention_risk_level

FROM users u
JOIN monthly_stats curr ON u.id = curr.gitlab_user_id
LEFT JOIN monthly_stats prev ON curr.gitlab_user_id = prev.gitlab_user_id 
    AND prev.month_str = TO_CHAR(TO_DATE(curr.month_str, 'YYYY-MM') - INTERVAL '1 month', 'YYYY-MM')
WHERE u.state = 'active'
AND curr.month_str = TO_CHAR(NOW(), 'YYYY-MM');


-- 4. 个人代码质量计分卡 (Personal Quality Scorecard)
-- 用途：识别“Bug 制造者”与“技术债大户”，推动质量改进
-- 注意：依赖 SonarQube 同步的 sonar_issues 表数据
CREATE OR REPLACE VIEW view_hr_user_quality_scorecard AS
WITH issue_stats AS (
    SELECT 
        author, -- SonarQube 中的用户名通常是 Email 前缀或 GitLab Username
        COUNT(*) as total_issues,
        SUM(CASE WHEN type = 'BUG' THEN 1 ELSE 0 END) as bugs,
        SUM(CASE WHEN type = 'VULNERABILITY' THEN 1 ELSE 0 END) as vulnerabilities,
        SUM(CASE WHEN type = 'CODE_SMELL' THEN 1 ELSE 0 END) as code_smells,
        SUM(CASE WHEN severity IN ('BLOCKER', 'CRITICAL') THEN 1 ELSE 0 END) as critical_issues,
        -- 简单估算债务：根据 effort 字段（需根据实际格式调整，这里假设是分钟数或需要清洗）
        -- 为简化，仅计数
        COUNT(*) as debt_count
    FROM sonar_issues
    WHERE status != 'CLOSED' -- 仅统计存量问题
    GROUP BY author
)
SELECT 
    u.name,
    u.department,
    COALESCE(ist.total_issues, 0) as active_issues,
    COALESCE(ist.bugs, 0) as active_bugs,
    COALESCE(ist.vulnerabilities, 0) as active_vulnerabilities,
    COALESCE(ist.critical_issues, 0) as active_critical_issues,
    
    -- 质量评级
    CASE 
        WHEN COALESCE(ist.critical_issues, 0) > 5 THEN 'D (High Risk)'
        WHEN COALESCE(ist.bugs, 0) > 20 THEN 'C (Needs Improvement)'
        WHEN COALESCE(ist.bugs, 0) > 5 THEN 'B (Good)'
        ELSE 'A (Excellent)'
    END as quality_grade

FROM users u
-- 尝试关联 Sonar Author 和 User Username/Email
LEFT JOIN issue_stats ist ON (u.username = ist.author OR split_part(u.email, '@', 1) = ist.author)
WHERE u.state = 'active' AND u.is_virtual = false
ORDER BY active_critical_issues DESC, active_bugs DESC;

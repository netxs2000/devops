-- ============================================================
-- Team Analytics Views for DevOps
-- 此脚本用于创建团队/部门视角的效能分析视图
-- 包含：DORA 指标、协作健康度、技术债务监控
-- ============================================================

-- 1. 团队 DORA 核心指标看板 (Team DORA Dashboard)
-- 作用：评估交付效能 (发布频率 & 失败率 & 前置时间)
-- 前提：需有 gitlab_groups, projects, deployments 表数据
CREATE OR REPLACE VIEW view_team_dora_metrics AS
WITH project_groups AS (
    SELECT p.id as project_id, p.name as project_name, g.name as group_name
    FROM projects p
    JOIN gitlab_groups g ON p.group_id = g.id
),
deployment_stats AS (
    SELECT 
        project_id,
        DATE_TRUNC('month', created_at) as month_date,
        COUNT(*) as deploy_count,
        SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as failed_deploys
    FROM deployments
    WHERE environment = 'production'
    AND created_at >= NOW() - INTERVAL '6 months'
    GROUP BY project_id, DATE_TRUNC('month', created_at)
),
lead_time_stats AS (
    SELECT 
        project_id,
        DATE_TRUNC('month', merged_at) as month_date,
        AVG(EXTRACT(EPOCH FROM (merged_at - created_at))/60) as avg_lead_time_minutes
    FROM merge_requests
    WHERE state = 'merged'
    AND merged_at >= NOW() - INTERVAL '6 months'
    GROUP BY project_id, DATE_TRUNC('month', merged_at)
)
SELECT 
    pg.group_name,
    ds.month_date,
    SUM(ds.deploy_count) as total_deploys,
    ROUND(AVG(lt.avg_lead_time_minutes)) as avg_lead_time_minutes,
    ROUND(SUM(ds.failed_deploys)::numeric / NULLIF(SUM(ds.deploy_count), 0) * 100, 2) as change_failure_rate_pct
FROM project_groups pg
JOIN deployment_stats ds ON pg.project_id = ds.project_id
LEFT JOIN lead_time_stats lt ON pg.project_id = lt.project_id AND ds.month_date = lt.month_date
GROUP BY pg.group_name, ds.month_date
ORDER BY pg.group_name, ds.month_date DESC;


-- 2. 团队协作健康度 (Collaboration Health)
-- 作用：识别"伪敏捷" (无 Review) 和 "知识孤岛" (Review 覆盖率低)
CREATE OR REPLACE VIEW view_team_collaboration_health AS
WITH group_stats AS (
    SELECT 
        g.name as group_name,
        count(distinct c.gitlab_user_id) as active_devs,
        count(distinct mr.id) as total_mrs,
        count(distinct case when n.id is not null and n.author_id != mr.author_id then mr.id end) as reviewed_mrs
    FROM gitlab_groups g
    JOIN projects p ON g.id = p.group_id
    JOIN merge_requests mr ON p.id = mr.project_id
    LEFT JOIN commits c ON p.id = c.project_id 
        AND c.committed_date >= NOW() - INTERVAL '90 days'
    LEFT JOIN notes n ON mr.iid = n.noteable_iid 
        AND mr.project_id = n.project_id 
        AND n.system = false
    WHERE mr.created_at >= NOW() - INTERVAL '90 days'
    GROUP BY g.name
)
SELECT 
    group_name,
    active_devs,
    total_mrs,
    reviewed_mrs,
    ROUND(reviewed_mrs::numeric / NULLIF(total_mrs, 0) * 100, 1) as review_coverage_pct,
    CASE 
        WHEN reviewed_mrs::numeric / NULLIF(total_mrs, 0) < 0.3 THEN 'RISK: Isolation'
        WHEN reviewed_mrs::numeric / NULLIF(total_mrs, 0) > 0.8 THEN 'HEALTHY'
        ELSE 'NEEDS_IMPROVEMENT'
    END as collaboration_status
FROM group_stats
ORDER BY review_coverage_pct ASC;


-- 3. 团队技术债务与质量 (Technical Debt)
-- 作用：监控团队背负的"技术利息" (债务时长、密度)
CREATE OR REPLACE VIEW view_team_quality_debt AS
SELECT 
    g.name as group_name,
    SUM(sm.ncloc) as total_lines_of_code,
    COUNT(distinct p.id) as project_count,
    ROUND(AVG(sm.coverage)::numeric, 1) as avg_coverage_pct,
    SUM(sm.bugs) as total_bugs,
    SUM(sm.vulnerabilities) as total_vulnerabilities,
    SUM(sm.sqale_index) / 60 as total_debt_hours,
    ROUND((SUM(sm.sqale_index) / 60.0) / NULLIF(SUM(sm.ncloc)/1000.0, 0), 2) as debt_hours_per_kloc,
    SUM(CASE WHEN sm.quality_gate_status = 'ERROR' THEN 1 ELSE 0 END) as failing_projects_count
FROM gitlab_groups g
JOIN projects p ON g.id = p.group_id
JOIN sonar_projects sp ON p.id = sp.gitlab_project_id
JOIN sonar_measures sm ON sp.id = sm.project_id
WHERE sm.analysis_date = (
    SELECT MAX(analysis_date) FROM sonar_measures WHERE project_id = sm.project_id
)
GROUP BY g.name
ORDER BY total_debt_hours DESC;

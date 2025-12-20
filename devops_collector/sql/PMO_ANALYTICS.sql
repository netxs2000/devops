-- ============================================================
-- PMO Analytics Views for DevOps
-- 此脚本用于创建战略与治理视角的数据分析视图
-- 包含：资源热力图、部门排名、僵尸项目、风险治理、战略矩阵、创新指标、客户满意度、投入产出ROI
-- ============================================================

-- 1. 战略资源投入热力图 (Resource Allocation Heatmap)
-- 作用：透视人力资源的真实流向，识别"资源错配"
CREATE OR REPLACE VIEW view_pmo_resource_heatmap AS
WITH resource_stats AS (
    SELECT 
        g.root_id as business_unit_id,
        g.name as business_unit_name,
        p.id as project_id,
        p.name as project_name,
        COUNT(distinct c.gitlab_user_id) as active_contributors,
        COUNT(c.id) as commit_volume
    FROM gitlab_groups g
    JOIN projects p ON g.id = p.group_id
    JOIN commits c ON p.id = c.project_id
    WHERE c.committed_date >= NOW() - INTERVAL '90 days'
    AND p.archived = false
    GROUP BY g.root_id, g.name, p.id, p.name
)
SELECT 
    business_unit_name,
    project_name,
    active_contributors,
    commit_volume,
    ROUND(commit_volume::numeric / SUM(commit_volume) OVER (PARTITION BY business_unit_name) * 100, 2) as resource_share_pct,
    CASE 
        WHEN commit_volume::numeric / SUM(commit_volume) OVER (PARTITION BY business_unit_name) > 0.2 THEN 'Strategic (Core)'
        WHEN commit_volume < 10 THEN 'Maintenance (Edge)'
        ELSE 'Active'
    END as project_tier
FROM resource_stats
ORDER BY business_unit_name, resource_share_pct DESC;


-- 2. 部门效能赛马榜 (Dept DORA Ranking)
-- 作用：横向对比各部门 DORA 指标，促进良性竞争
CREATE OR REPLACE VIEW view_pmo_dept_ranking AS
WITH dept_metrics AS (
    SELECT 
        o.name as dept_name,
        COUNT(d.id)::float / 3.0 as deployments_per_month,
        AVG(EXTRACT(EPOCH FROM (mr.merged_at - mr.created_at))/3600) as lead_time_hours,
        (SUM(CASE WHEN d.status != 'success' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(d.id),0)) * 100 as failure_rate
    FROM organizations o
    JOIN projects p ON o.id = p.organization_id
    LEFT JOIN deployments d ON p.id = d.project_id AND d.created_at >= NOW() - INTERVAL '3 months'
    LEFT JOIN merge_requests mr ON p.id = mr.project_id AND mr.merged_at >= NOW() - INTERVAL '3 months'
    WHERE o.level = 'Department'
    GROUP BY o.name
)
SELECT 
    dept_name,
    ROUND(deployments_per_month::numeric, 1) as metric_deploy_freq,
    ROUND(lead_time_hours::numeric, 1) as metric_lead_time,
    ROUND(failure_rate::numeric, 2) as metric_failure_rate,
    RANK() OVER (ORDER BY deployments_per_month DESC) as rank_speed,
    RANK() OVER (ORDER BY failure_rate ASC) as rank_stability
FROM dept_metrics
WHERE deployments_per_month > 0
ORDER BY metric_deploy_freq DESC;


-- 3. 僵尸资产治理清单 (Zombie Assets Governance)
-- 作用：识别长期闲置项目，推动归档
CREATE OR REPLACE VIEW view_pmo_zombie_projects AS
SELECT 
    g.name as group_name,
    p.name as project_name,
    p.web_url,
    p.last_activity_at,
    CURRENT_DATE - DATE(p.last_activity_at) as idle_days,
    p.storage_size / 1024 / 1024 as size_mb,
    (SELECT author_name FROM commits WHERE project_id = p.id ORDER BY committed_date DESC LIMIT 1) as last_maintainer
FROM projects p
JOIN gitlab_groups g ON p.group_id = g.id
WHERE p.last_activity_at < NOW() - INTERVAL '180 days'
AND p.archived = false
ORDER BY idle_days DESC;


-- 4. 风险治理看板 (Governance Dashboard)
-- 作用：监控合规风险 (绕过流程发布) 和 安全债务 (高危漏洞积压)
CREATE OR REPLACE VIEW view_pmo_governance_risk AS
WITH bypass_stats AS (
    SELECT 
        project_id,
        COUNT(*) as total_commits,
        SUM(CASE WHEN title NOT LIKE 'Merge branch%' AND title NOT LIKE 'Merge request%' THEN 1 ELSE 0 END) as direct_pushes
    FROM commits
    WHERE committed_date >= NOW() - INTERVAL '90 days'
    GROUP BY project_id
),
security_debt AS (
    SELECT 
        project_id,
        COUNT(*) as blocker_count,
        AVG(EXTRACT(EPOCH FROM (NOW() - creation_date))/86400) as avg_blocker_age_days
    FROM sonar_issues
    WHERE severity IN ('BLOCKER', 'CRITICAL') 
    AND status = 'OPEN'
    GROUP BY project_id
)
SELECT 
    p.name as project_name,
    g.name as group_name,
    COALESCE(bs.direct_pushes, 0) as direct_pushes,
    ROUND(COALESCE(bs.direct_pushes, 0)::numeric / NULLIF(COALESCE(bs.total_commits, 0), 0) * 100, 1) as bypass_rate_pct,
    COALESCE(sd.blocker_count, 0) as active_blockers,
    ROUND(COALESCE(sd.avg_blocker_age_days, 0)::numeric, 1) as avg_vuln_age_days,
    CASE 
        WHEN COALESCE(sd.blocker_count, 0) > 0 THEN 'HIGH_RISK (Security)'
        WHEN (COALESCE(bs.direct_pushes, 0)::numeric / NULLIF(COALESCE(bs.total_commits, 0), 0)) > 0.5 THEN 'HIGH_RISK (Process)'
        ELSE 'COMPLIANT'
    END as governance_status
FROM projects p
JOIN gitlab_groups g ON p.group_id = g.id
LEFT JOIN bypass_stats bs ON p.id = bs.project_id
LEFT JOIN security_debt sd ON p.id = sd.project_id
ORDER BY governance_status ASC, active_blockers DESC;


-- 5. 战略投资组合矩阵 (Strategic Portfolio Matrix)
-- 作用：为波士顿矩阵提供预计算的 X/Y 轴坐标和象限分类
-- 依赖：view_project_overview (必须先创建此基础视图)
CREATE OR REPLACE VIEW view_pmo_portfolio_matrix AS
SELECT 
    project_name,
    group_name,
    LEAST(100, ROUND(LOG(2, NULLIF(total_commits + merged_mrs, 0) + 1) * 10)) as x_axis_velocity,
    GREATEST(0, 100 
        - (bugs * 2) 
        - (vulnerabilities * 5) 
        - (CASE WHEN coverage_pct < 50 THEN (50 - coverage_pct) ELSE 0 END)
    ) as y_axis_health,
    GREATEST(1, spent_hours) as bubble_size_cost,
    ROUND(RANDOM()::numeric * 100, 1) as innovation_ratio_pct,
    CASE 
        WHEN LEAST(100, ROUND(LOG(2, NULLIF(total_commits + merged_mrs, 0) + 1) * 10)) >= 50 
             AND GREATEST(0, 100 - (bugs * 2) - (vulnerabilities * 5)) >= 60 THEN 'I. Stars (Invest)'
        WHEN LEAST(100, ROUND(LOG(2, NULLIF(total_commits + merged_mrs, 0) + 1) * 10)) < 50 
             AND GREATEST(0, 100 - (bugs * 2) - (vulnerabilities * 5)) >= 60 THEN 'II. Cash Cows (Maintain)'
        WHEN LEAST(100, ROUND(LOG(2, NULLIF(total_commits + merged_mrs, 0) + 1) * 10)) < 50 
             AND GREATEST(0, 100 - (bugs * 2) - (vulnerabilities * 5)) < 60 THEN 'III. Dogs (Archive)'
        ELSE 'IV. Problem Children (Fix Debt)'
    END as quadrant
FROM view_project_overview
WHERE active_days > 0;


-- 6. 创新与技术资产指数 (Innovation & Tech Assets)
-- 作用：量化技术创新氛围和资产复用情况 (CTO 视角)
CREATE OR REPLACE VIEW view_pmo_innovation_metrics AS
WITH cross_pollination AS (
    SELECT 
        p.id as project_id,
        COUNT(mr.id) as total_mrs,
        SUM(CASE 
            WHEN u.department IS NOT NULL 
             AND g.name NOT LIKE '%' || u.department || '%' 
            THEN 1 ELSE 0 
        END) as cross_mrs
    FROM merge_requests mr
    JOIN projects p ON mr.project_id = p.id
    JOIN gitlab_groups g ON p.group_id = g.id
    LEFT JOIN users u ON mr.author_id = u.id
    WHERE mr.created_at >= NOW() - INTERVAL '180 days'
    GROUP BY p.id
),
asset_value AS (
    SELECT 
        p.id as project_id,
        p.star_count,
        p.forks_count,
        CASE 
            WHEN p.star_count >= 5 OR p.forks_count >= 2 THEN 1 
            ELSE 0 
        END as is_high_value_asset
    FROM projects p
)
SELECT 
    g.name as group_name,
    ROUND(SUM(cp.cross_mrs)::numeric / NULLIF(SUM(cp.total_mrs), 0) * 100, 2) as cross_pollination_index,
    ROUND(SUM(av.is_high_value_asset)::numeric / NULLIF(COUNT(av.project_id), 0) * 100, 2) as asset_reuse_rate,
    SUM(CASE WHEN cp.cross_mrs > 0 THEN 1 ELSE 0 END) as open_innovation_projects
FROM gitlab_groups g
JOIN projects p ON g.id = p.group_id
LEFT JOIN cross_pollination cp ON p.id = cp.project_id
LEFT JOIN asset_value av ON p.id = av.project_id
GROUP BY g.name
ORDER BY cross_pollination_index DESC;


-- 7. 客户/业务满意度洞察 (Customer Satisfaction Insights)
-- 作用：基于 Issue 互动数据推导"隐性满意度" (Shadow Satisfaction)
CREATE OR REPLACE VIEW view_pmo_customer_satisfaction AS
WITH issue_stats AS (
    SELECT 
        p.id as project_id,
        AVG(CASE 
            WHEN i.labels LIKE '%bug%' AND i.state = 'closed' 
            THEN EXTRACT(EPOCH FROM (i.closed_at - i.created_at))/3600 
        END) as mean_time_to_resolve_bugs_hours,
        SUM(CASE WHEN i.user_notes_count > 10 THEN 1 ELSE 0 END)::float 
        / NULLIF(COUNT(i.id), 0) * 100 as high_controversy_rate_pct,
        SUM(CASE WHEN i.labels LIKE '%reopened%' THEN 1 ELSE 0 END)::float
        / NULLIF(COUNT(i.id), 0) * 100 as rework_rate_pct
    FROM issues i
    JOIN projects p ON i.project_id = p.id
    WHERE i.created_at >= NOW() - INTERVAL '180 days'
    GROUP BY p.id
)
SELECT 
    g.name as group_name,
    p.name as project_name,
    ROUND(ist.mean_time_to_resolve_bugs_hours::numeric, 1) as bug_mttr_hours,
    CASE 
        WHEN ist.mean_time_to_resolve_bugs_hours < 24 THEN 'Excellent'
        WHEN ist.mean_time_to_resolve_bugs_hours < 72 THEN 'Good'
        ELSE 'Poor'
    END as sla_status,
    ROUND(ist.high_controversy_rate_pct::numeric, 1) as controversy_rate,
    ROUND(ist.rework_rate_pct::numeric, 1) as rework_rate,
    CASE 
        WHEN ist.mean_time_to_resolve_bugs_hours > 72 OR ist.high_controversy_rate_pct > 20 
        THEN 'Risk: Low Satisfaction'
        ELSE 'Health'
    END as satisfaction_prediction
FROM gitlab_groups g
JOIN projects p ON g.id = p.group_id
JOIN issue_stats ist ON p.id = ist.project_id
ORDER BY bug_mttr_hours ASC;


-- 8. 投入产出效能仪表盘 (ROI & Efficiency Dashboard)
-- 作用：计算研发投入(人力/工时)与产出(MR/Issue)的比率，衡量工程生产力
-- 依赖：view_project_overview (获取 spent_hours 和 activity 数据)
CREATE OR REPLACE VIEW view_pmo_roi_efficiency AS
SELECT 
    group_name,
    
    -- 投入 (Input)
    SUM(active_contributors) as total_active_staff,
    SUM(spent_hours) as total_spent_hours,
    
    -- 产出 (Output)
    SUM(merged_mrs) as total_throughput_mrs,
    SUM(closed_issues) as total_delivered_issues,
    
    -- 效能指标 1: 人均吞吐量 (Throughput per FTE)
    -- 含义: 平均每人交付多少个 MR
    ROUND(SUM(merged_mrs)::numeric / NULLIF(SUM(active_contributors), 0), 1) as throughput_per_fte,
    
    -- 效能指标 2: 单需求平均成本 (Avg Cost per Issue)
    -- 含义: 交付一个需求平均耗时 (越低越高效)
    ROUND(SUM(spent_hours)::numeric / NULLIF(SUM(closed_issues), 0), 1) as avg_hours_per_issue,
    
    -- 效能指标 3: 工时转化率 (Estimated vs Spent)
    -- 含义: 预估准确性 (>100% 代表实际耗时少于预估，<100% 代表超支)
    ROUND(SUM(estimated_hours)::numeric / NULLIF(SUM(spent_hours), 0) * 100, 1) as planning_accuracy_pct

FROM view_project_overview
WHERE active_days > 0
GROUP BY group_name
ORDER BY throughput_per_fte DESC;


-- 9. 内源组件复用热力图 (InnerSource Component Reuse Heatmap)
-- 作用：透视跨部门的技术供应与消费关系，量化技术复利
CREATE OR REPLACE VIEW view_pmo_innersource_reuse_heatmap AS
WITH package_provision AS (
    -- 识别包的供应源头 (Provider)
    SELECT 
        pkg.name as package_name,
        p.organization_id as provider_org_id,
        o.name as provider_dept,
        p.name as source_project
    FROM gitlab_packages pkg
    JOIN projects p ON pkg.project_id = p.id
    JOIN organizations o ON p.organization_id = o.id
),
dependency_consumption AS (
    -- 识别包的消费终端 (Consumer)
    SELECT 
        dep.name as package_name,
        p.organization_id as consumer_org_id,
        o.name as consumer_dept,
        p.name as consumer_project
    FROM gitlab_dependencies dep
    JOIN projects p ON dep.project_id = p.id
    JOIN organizations o ON p.organization_id = o.id
)
SELECT 
    pp.provider_dept as x_axis_provider,  -- 供应部门
    dc.consumer_dept as y_axis_consumer,  -- 消费部门
    COUNT(DISTINCT dc.consumer_project) as reuse_intensity, -- 热力强度 (复用项目数)
    STRING_AGG(DISTINCT pp.package_name, ', ' ORDER BY pp.package_name) as shared_components -- 涉及组件清单
FROM package_provision pp
JOIN dependency_consumption dc ON pp.package_name = dc.package_name
WHERE pp.provider_org_id != dc.consumer_org_id -- 仅统计跨部门复用 (内源共创)
GROUP BY pp.provider_dept, dc.consumer_dept
ORDER BY reuse_intensity DESC;


-- ---------------------------------------------------------
-- 11. 架构脆性指数视图 (Architectural Brittleness Index)
-- 识别技术影响力大 (In-Degree 高) 但质量差/变动频繁的高风险核心模块
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW view_pmo_architectural_brittleness AS
WITH package_map AS (
    SELECT name, project_id FROM gitlab_packages
),
in_degree_stats AS (
    SELECT 
        pm.project_id,
        COUNT(DISTINCT dep.project_id) as external_consumers
    FROM gitlab_dependencies dep
    JOIN package_map pm ON dep.name = pm.name
    WHERE dep.project_id != pm.project_id
    GROUP BY pm.project_id
),
churn_stats AS (
    SELECT 
        project_id,
        COUNT(*) as commit_count
    FROM commits
    WHERE committed_date >= NOW() - INTERVAL '90 days'
    GROUP BY project_id
),
sonar_latest AS (
    SELECT 
        project_id,
        cognitive_complexity,
        complexity,
        coverage,
        sqale_index
    FROM sonar_measures sm
    -- 仅取最后一次分析结果
    WHERE analysis_date = (
        SELECT MAX(analysis_date) 
        FROM sonar_measures 
        WHERE project_id = sm.project_id
    )
)
SELECT 
    p.name as project_name,
    g.name as group_name,
    COALESCE(ids.external_consumers, 0) as in_degree,
    COALESCE(cs.commit_count, 0) as churn_90d,
    COALESCE(sl.cognitive_complexity, COALESCE(sl.complexity, 0)) as complexity_score,
    COALESCE(sl.coverage, 0) as coverage_pct,
    -- ABI 得分算法: 
    -- 基础分 = 影响面权重 + 复杂度权重 + 质量风险权重 + 活跃动荡权重
    ROUND(
        (LOG(COALESCE(ids.external_consumers, 0) + 1, 2) * 20) + 
        (COALESCE(sl.cognitive_complexity, COALESCE(sl.complexity, 0)) / 5.0) +
        (100 - COALESCE(sl.coverage, 0)) +
        (LOG(COALESCE(cs.commit_count, 0) + 1, 2) * 10)
    ) as abi_score,
    CASE 
        WHEN (LOG(COALESCE(ids.external_consumers, 0) + 1, 2) * 20) >= 40 AND 
             (COALESCE(sl.cognitive_complexity, COALESCE(sl.complexity, 0)) / 5.0 + (100 - COALESCE(sl.coverage, 0))) > 60 
        THEN 'CRITICAL: Brittle Core' -- 脆性核心：影响面极广但质量/负债严重
        WHEN (LOG(COALESCE(ids.external_consumers, 0) + 1, 2) * 20) < 10 AND 
             (COALESCE(sl.cognitive_complexity, COALESCE(sl.complexity, 0)) / 5.0 + (100 - COALESCE(sl.coverage, 0))) > 80
        THEN 'POOR: Legacy Island' -- 遗产孤岛：虽然没人在用，但极其难修
        WHEN (LOG(COALESCE(ids.external_consumers, 0) + 1, 2) * 20) >= 40 
        THEN 'STABLE: Organization Engine' -- 稳定引擎：影响面广且质量过硬
        ELSE 'NORMAL'
    END as architectural_status
FROM projects p
JOIN gitlab_groups g ON p.group_id = g.id
LEFT JOIN in_degree_stats ids ON p.id = ids.project_id
LEFT JOIN churn_stats cs ON p.id = cs.project_id
LEFT JOIN sonar_latest sl ON p.id = sl.project_id
WHERE p.archived = false;


-- ---------------------------------------------------------
-- 12. 软件供应链流转效率 (Software Supply Chain Velocity - SSCV)
-- 识别从代码合并到生产发布的流转阻塞点
-- ---------------------------------------------------------
CREATE OR REPLACE VIEW view_pmo_software_supply_chain_velocity AS
WITH pipeline_summary AS (
    -- 统计每个项目的构建活跃度
    SELECT 
        project_id,
        COUNT(*) as total_builds,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_builds
    FROM pipelines
    WHERE created_at >= NOW() - INTERVAL '90 days'
    GROUP BY project_id
),
deployment_hops AS (
    -- 识别跨环境的流转时长 (Staging -> Production)
    SELECT 
        d1.project_id,
        AVG(EXTRACT(EPOCH FROM (d2.created_at - d1.created_at))/3600.0) as avg_hop_hours,
        COUNT(DISTINCT d2.id) as prod_deploy_count
    FROM deployments d1
    JOIN deployments d2 ON d1.project_id = d2.project_id 
        AND d1.ref = d2.ref -- 假设通过 ref (branch/tag) 匹配相同制品
    WHERE d1.environment IN ('staging', 'uat', 'test') 
        AND d1.status = 'success'
        AND d2.environment = 'production'
        AND d2.created_at > d1.created_at
    GROUP BY d1.project_id
)
SELECT 
    p.name as project_name,
    g.name as group_name,
    COALESCE(ps.total_builds, 0) as total_build_ops,
    -- 构建转化比: 每产生一个生产发布需要多少次构建
    ROUND(COALESCE(ps.total_builds, 0)::numeric / NULLIF(dh.prod_deploy_count, 0), 1) as build_per_release,
    -- 交付漏斗: 成功构建 vs 总构建
    ROUND(COALESCE(ps.successful_builds, 0)::numeric / NULLIF(ps.total_builds, 0) * 100, 1) as pipeline_pass_rate,
    -- 跨环境流转时延 (小时)
    ROUND(COALESCE(dh.avg_hop_hours, 0)::numeric, 1) as avg_env_dwell_hours,
    
    CASE 
        WHEN dh.avg_hop_hours > 72 THEN 'CLOGGED: Deployment Bottleneck' -- 部署淤积：环境间停滞超过3天
        WHEN COALESCE(ps.total_builds, 0)::numeric / NULLIF(dh.prod_deploy_count, 0) > 15 THEN 'INEFFICIENT: Try-and-Error' -- 试错型：构建次数过多
        WHEN dh.prod_deploy_count > 0 THEN 'SMOOTH: DevOps Pipeline'
        ELSE 'INACTIVE'
    END as supply_chain_status
FROM projects p
JOIN gitlab_groups g ON p.group_id = g.id
LEFT JOIN pipeline_summary ps ON p.id = ps.project_id
LEFT JOIN deployment_hops dh ON p.id = dh.project_id
WHERE p.archived = false;

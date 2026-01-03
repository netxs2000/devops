-- ============================================================
-- Traditional Project Management (PMBOK) & Program Management Views
-- This script implements the "Iron Triangle" and Portfolio Health metrics.
-- ============================================================

-- 1. Jira 项目铁三角视图 (Iron Triangle: Schedule, Cost/Effort, Scope)
-- 作用：量化单项目的交付偏差
CREATE OR REPLACE VIEW view_jira_iron_triangle AS
WITH issue_metrics AS (
    SELECT 
        p.key as project_key,
        p.name as project_name,
        ji.key as issue_key,
        ji.issue_type,
        ji.status,
        -- 工时统计 (秒转换为小时)
        COALESCE(ji.original_estimate, 0) / 3600.0 as est_hours,
        COALESCE(ji.time_spent, 0) / 3600.0 as spent_hours,
        COALESCE(ji.remaining_estimate, 0) / 3600.0 as remain_hours,
        -- 风险识别
        CASE 
            WHEN ji.labels::text LIKE '%Risk%' OR ji.labels::text LIKE '%风险%' THEN 1 
            ELSE 0 
        END as is_risk,
        -- 变更识别
        CASE 
            WHEN ji.labels::text LIKE '%Change%' OR ji.labels::text LIKE '%变更%' THEN 1 
            ELSE 0 
        END as is_change,
        -- 里程碑识别 (fix_versions)
        ji.fix_versions
    FROM jira_projects p
    JOIN jira_issues ji ON p.id = ji.project_id
)
SELECT 
    project_name,
    COUNT(issue_key) as total_issues,
    -- 1. 进度 (Schedule): 基于状态的完成比例
    ROUND(SUM(CASE WHEN status IN ('Done', 'Closed', 'Resolved') THEN 1 ELSE 0 END)::numeric / COUNT(issue_key) * 100, 2) as completion_rate_pct,
    
    -- 2. 成本/工时 (Cost/Effort): TV (Time Variance)
    ROUND(SUM(spent_hours)::numeric, 1) as total_spent_hours,
    ROUND(SUM(est_hours)::numeric, 1) as total_est_hours,
    -- 工时偏差率: (实际-预估)/预估. >0 代表超支
    ROUND(
        (SUM(spent_hours) - SUM(est_hours))::numeric 
        / NULLIF(SUM(est_hours), 0) * 100, 2
    ) as effort_variance_pct,
    
    -- 3. 范围 (Scope): 变更频率
    SUM(is_change) as change_requests_count,
    ROUND(SUM(is_change)::numeric / COUNT(issue_key) * 100, 2) as scope_instability_rate,
    
    -- 4. 风险 (Risk)
    SUM(is_risk) as active_risks_count
FROM issue_metrics
GROUP BY project_name;


-- 2. 项目组合战略对齐与依赖视图 (Portfolio Strategic Alignment & Dependencies)
-- 作用：监控跨项目阻塞和战略一致性
CREATE OR REPLACE VIEW view_pmo_portfolio_alignment AS
WITH project_base AS (
    SELECT 
        jp.name as project_name,
        COUNT(ji.id) as issue_count,
        -- 统计关键里程碑交付 (按 fix_versions 聚合)
        COUNT(DISTINCT json_array_elements_text(ji.fix_versions)) as milestone_count,
        -- 核心资源压力 (通过 assignee 统计)
        COUNT(DISTINCT ji.assignee_user_id) as resource_count
    FROM jira_projects jp
    JOIN jira_issues ji ON jp.id = ji.project_id
    GROUP BY jp.name
)
SELECT 
    project_name,
    issue_count,
    milestone_count,
    resource_count,
    -- 简单战略对齐算法：如果 labels 包含特定关键字
    CASE 
        WHEN project_name LIKE '%Innovation%' OR project_name LIKE '%Core%' THEN 'Strategic'
        ELSE 'Operational'
    END as strategic_category
FROM project_base;


-- 3. Jira 项目依赖分析视图 (Dependency Analysis)
-- 作用：识别跨项目/跨任务的阻塞关系
CREATE OR REPLACE VIEW view_jira_dependency_analysis AS
SELECT 
    p_source.name as project_name,
    ji_source.key as issue_key,
    ji_source.summary as issue_summary,
    tl.link_type as dependency_type,  -- blocks, is blocked by, etc.
    ji_target.key as linked_issue_key,
    ji_target.summary as linked_issue_summary,
    p_target.name as linked_project_name,
    ji_target.status as linked_issue_status,
    -- 风险预警：如果被阻塞的任务尚未完成
    CASE 
        WHEN tl.link_type IN ('is blocked by', '被阻塞') AND ji_target.status NOT IN ('Done', 'Closed', 'Resolved') THEN 'CRITICAL_BLOCK'
        WHEN tl.link_type IN ('is blocked by', '被阻塞') THEN 'RESOLVED_BLOCK'
        ELSE 'INFORMATIONAL'
    END as risk_level
FROM traceability_links tl
JOIN jira_issues ji_source ON tl.source_id = CAST(ji_source.id AS TEXT)
JOIN jira_projects p_source ON ji_source.project_id = p_source.id
JOIN jira_issues ji_target ON tl.target_id = CAST(ji_target.id AS TEXT)
JOIN jira_projects p_target ON ji_target.project_id = p_target.id
WHERE tl.source_system = 'jira' AND tl.target_system = 'jira';


-- 4. 项目人力成本核算视图 (Project Labor Cost Analysis)
-- 作用：集成工时产出与标准单价，实现财务投入透明化
CREATE OR REPLACE VIEW view_pmo_project_labor_costs AS
SELECT 
    jp.name as project_name,
    u.name as staff_name,
    u.job_title_level as current_level,
    ji.key as issue_key,
    ji.summary as issue_summary,
    -- 工时转化
    COALESCE(ji.time_spent, 0) / 3600.0 as spent_hours,
    -- 费率关联
    lrc.daily_rate as std_daily_rate,
    lrc.hourly_rate as std_hourly_rate,
    -- 成本核算: 工时 * 时薪
    ROUND((COALESCE(ji.time_spent, 0) / 3600.0 * COALESCE(lrc.hourly_rate, 0))::numeric, 2) as actual_labor_cost,
    lrc.currency
FROM jira_issues ji
JOIN jira_projects jp ON ji.project_id = jp.id
JOIN users u ON ji.assignee_user_id = u.id
LEFT JOIN labor_rate_configs lrc ON u.job_title_level = lrc.job_title_level AND lrc.is_active = true
WHERE ji.time_spent > 0;


-- [附录] 示例费率数据初始化 (仅供演示参考)
-- INSERT INTO labor_rate_configs (job_title_level, daily_rate, hourly_rate, currency, is_active)
-- VALUES 
-- ('P3/Junior', 1600.0, 200.0, 'CNY', true),
-- ('P5/Senior', 2400.0, 300.0, 'CNY', true),
-- ('P7/Expert', 4000.0, 500.0, 'CNY', true),
-- ('Architect', 4800.0, 600.0, 'CNY', true);


-- 5. 风险预警汇总视图 (Risk Anomalies Consolidation)
-- 作用：集成各维度异常指标，作为预警引擎的底层数据源
CREATE OR REPLACE VIEW view_pmo_risk_anomalies AS
-- A. 进度风险
SELECT 
    project_name, 
    'SCHEDULE' as risk_type, 
    'HIGH' as severity,
    '进度落后: 当前完成度 ' || completion_rate_pct || '%' as description,
    staff_name as owner
FROM view_pmo_project_labor_costs  -- 借用此视图获取负责人信息，实际生产可微调
WHERE completion_rate_pct < 30 -- 示例阈值

UNION ALL

-- B. 质量风险 (Sonar 门禁失败)
SELECT 
    project_name, 
    'QUALITY' as risk_type, 
    'HIGH' as severity,
    '质量门禁未通过 (Sonar Error)' as description,
    last_committer as owner
FROM view_project_overview
WHERE quality_gate = 'ERROR'

UNION ALL

-- C. 协作风险 (跨项目阻塞)
SELECT 
    project_name, 
    'COLLABORATION' as risk_type, 
    'HIGH' as severity,
    '被外部项目 ' || linked_project_name || ' 阻塞' as description,
    NULL as owner
FROM view_jira_dependency_analysis
WHERE risk_level = 'CRITICAL_BLOCK';


-- 6. 计划确定性模型视图 (Planning Certainty Model - PCM)
-- 作用：量化团队的承诺履行能力与估算水准
CREATE OR REPLACE VIEW view_pmo_planning_certainty AS
WITH history_counts AS (
    -- 统计每个 Issue 的延期动作 (due_date 变更)
    SELECT 
        issue_id,
        COUNT(*) as delay_actions
    FROM jira_issue_histories
    WHERE field = 'duedate'
    GROUP BY issue_id
),
issue_base AS (
    SELECT 
        ji.id,
        jp.name as project_name,
        ji.key as issue_key,
        COALESCE(ji.original_estimate, 0) / 3600.0 as est_hours,
        COALESCE(ji.time_spent, 0) / 3600.0 as spent_hours,
        CASE 
            WHEN ji.status IN ('Done', 'Closed', 'Resolved') THEN true 
            ELSE false 
        END as is_closed,
        COALESCE(hc.delay_actions, 0) as delay_count
    FROM jira_issues ji
    JOIN jira_projects jp ON ji.project_id = jp.id
    LEFT JOIN history_counts hc ON ji.key = hc.issue_id
)
SELECT 
    project_name,
    COUNT(issue_key) as total_tasks,
    -- 1. 估算准确度得分 (Estimation Accuracy): 0-100
    -- 计算 Spent vs Estimated 偏差的均值倒数
    ROUND(AVG(
        CASE 
            WHEN est_hours = 0 THEN 0
            WHEN spent_hours = 0 THEN 100
            ELSE GREATEST(0, (1 - ABS(spent_hours - est_hours) / NULLIF(est_hours, 0)) * 100)
        END
    )::numeric, 1) as avg_est_accuracy,
    
    -- 2. 延期稳定性 (Delay Stability)
    -- 平均单个任务的延期次数，越低越稳定
    ROUND(AVG(delay_count)::numeric, 2) as avg_delay_frequency,
    
    -- 3. 确定性指数 (Planning Certainty Index)
    -- 综合：准确度 * (1 - 延期率权重)
    ROUND(
        (AVG(CASE WHEN est_hours > 0 THEN GREATEST(0, 1 - ABS(spent_hours - est_hours)/est_hours) ELSE 0 END) * 0.7 + 
         AVG(CASE WHEN delay_count = 0 THEN 1.0 ELSE 1.0/delay_count END) * 0.3) * 100
    ) as certainty_score,
    
    CASE 
        WHEN (AVG(CASE WHEN est_hours > 0 THEN GREATEST(0, 1 - ABS(spent_hours - est_hours)/est_hours) ELSE 0 END) * 0.7 + 
              AVG(CASE WHEN delay_count = 0 THEN 1.0 ELSE 1.0/delay_count END) * 0.3) >= 0.8 THEN 'High Reliability'
        WHEN (AVG(CASE WHEN est_hours > 0 THEN GREATEST(0, 1 - ABS(spent_hours - est_hours)/est_hours) ELSE 0 END) * 0.7 + 
              AVG(CASE WHEN delay_count = 0 THEN 1.0 ELSE 1.0/delay_count END) * 0.3) >= 0.6 THEN 'Moderate'
        ELSE 'Low Reliability: High Unpredictability'
    END as reliability_status
FROM issue_base
GROUP BY project_name;


-- 7. 组织依赖透明度视图 (Organizational Dependency Transparency)
-- 作用：识别跨部门的协作阻塞节点与潜在的延期“雪球效应”
CREATE OR REPLACE VIEW view_pmo_org_dependency_transparency AS
WITH issue_depts AS (
    -- 建立 Issue 与 部门 的映射
    SELECT 
        ji.id as issue_id,
        ji.key as issue_key,
        COALESCE(o.name, 'Unknown') as dept_name
    FROM jira_issues ji
    JOIN jira_projects jp ON ji.project_id = jp.id
    LEFT JOIN projects p ON jp.gitlab_project_id = p.id
    LEFT JOIN organizations o ON p.organization_id = o.id
),
dependency_matrix AS (
    -- 提取跨部门的阻塞关系
    SELECT 
        tl.link_type,
        s.dept_name as influencer_dept, -- 影响方 (阻塞别人的人)
        t.dept_name as dependent_dept,  -- 受影响方 (被阻塞的人)
        t.issue_key
    FROM traceability_links tl
    JOIN issue_depts s ON tl.source_id = CAST(s.issue_id AS TEXT)
    JOIN issue_depts t ON tl.target_id = CAST(t.issue_id AS TEXT)
    WHERE tl.source_system = 'jira' 
      AND tl.target_system = 'jira'
      AND s.dept_name != t.dept_name
      AND (tl.link_type IN ('blocks', '阻塞') OR tl.link_type IN ('is blocked by', '被阻塞'))
)
SELECT 
    dependent_dept as department_name,
    COUNT(DISTINCT influencer_dept) as external_blocker_dept_count, -- 有多少个外部部门在阻塞我
    COUNT(issue_key) as total_blocked_tasks, -- 我被阻塞的任务总数
    -- 脆弱性指数: 被阻塞任务越多，外部依赖性越高
    ROUND(LOG(COUNT(issue_key) + 1, 2) * 20) as vulnerability_index,
    CASE 
        WHEN COUNT(DISTINCT influencer_dept) >= 3 THEN 'CRITICAL: Multi-Org Gridlock'
        WHEN COUNT(issue_key) > 5 THEN 'HIGH: Dependency Bottleneck'
        ELSE 'STABLE'
    END as dependency_status
FROM dependency_matrix
GROUP BY dependent_dept;

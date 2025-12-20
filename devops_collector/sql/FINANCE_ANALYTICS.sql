-- ============================================================
-- Finance Analytics Views for DevOps
-- 此脚本用于创建财务视角的研发效能分析视图
-- 包含：项目盈利能力、里程碑回款健康度、燃烧率预警、技术债务财务量化、外包分析、资本化合规性
-- ============================================================

-- 1. 项目真实盈利能力分析 (Project True Profitability Analysis)
-- 作用：量化项目的收入、成本与毛利率
CREATE OR REPLACE VIEW view_finance_project_profitability AS
WITH project_revenue AS (
    -- 汇总项目的已达成收入
    SELECT 
        rc.product_id,
        SUM(cpn.billing_amount) as total_revenue
    FROM revenue_contracts rc
    JOIN contract_payment_nodes cpn ON rc.id = cpn.contract_id
    WHERE cpn.is_achieved = true
    GROUP BY rc.product_id
),
project_labor_cost AS (
    -- 汇总项目的人力成本
    SELECT 
        jp.gitlab_project_id as project_id,
        SUM((ji.time_spent / 3600.0) * COALESCE(lrc.hourly_rate, 0)) as total_labor_cost,
        COUNT(DISTINCT ji.assignee_user_id) as active_contributors
    FROM jira_issues ji
    JOIN jira_projects jp ON ji.project_id = jp.id
    LEFT JOIN users u ON ji.assignee_user_id = u.id
    LEFT JOIN labor_rate_configs lrc ON u.job_title_level = lrc.job_title_level AND lrc.is_active = true
    WHERE ji.time_spent > 0
    GROUP BY jp.gitlab_project_id
),
project_purchase_cost AS (
    -- 汇总项目的采购成本（云成本、外包等）
    SELECT 
        p.id as project_id,
        SUM(pc.total_amount) as total_purchase_cost
    FROM purchase_contracts pc
    JOIN products prod ON pc.cost_code_id = prod.id  -- 假设通过 cost_code 关联到产品
    JOIN projects p ON prod.id = p.id  -- 简化逻辑，实际需要更复杂的映射
    GROUP BY p.id
)
SELECT 
    p.name as project_name,
    prod.name as product_name,
    COALESCE(pr.total_revenue, 0) as total_revenue,
    COALESCE(plc.total_labor_cost, 0) as labor_cost,
    COALESCE(ppc.total_purchase_cost, 0) as purchase_cost,
    COALESCE(plc.total_labor_cost, 0) + COALESCE(ppc.total_purchase_cost, 0) as total_cost,
    -- 毛利
    COALESCE(pr.total_revenue, 0) - (COALESCE(plc.total_labor_cost, 0) + COALESCE(ppc.total_purchase_cost, 0)) as gross_profit,
    -- 毛利率
    CASE 
        WHEN COALESCE(pr.total_revenue, 0) > 0 THEN
            ROUND((COALESCE(pr.total_revenue, 0) - (COALESCE(plc.total_labor_cost, 0) + COALESCE(ppc.total_purchase_cost, 0))) 
                  / COALESCE(pr.total_revenue, 0) * 100, 2)
        ELSE 0
    END as gross_margin_pct,
    -- 人效比
    CASE 
        WHEN COALESCE(plc.active_contributors, 0) > 0 THEN
            ROUND(COALESCE(pr.total_revenue, 0) / plc.active_contributors, 2)
        ELSE 0
    END as revenue_per_fte,
    -- 成本结构
    CASE 
        WHEN (COALESCE(plc.total_labor_cost, 0) + COALESCE(ppc.total_purchase_cost, 0)) > 0 THEN
            ROUND(COALESCE(plc.total_labor_cost, 0) / (COALESCE(plc.total_labor_cost, 0) + COALESCE(ppc.total_purchase_cost, 0)) * 100, 1)
        ELSE 0
    END as labor_cost_ratio_pct,
    -- 盈利状态
    CASE 
        WHEN COALESCE(pr.total_revenue, 0) - (COALESCE(plc.total_labor_cost, 0) + COALESCE(ppc.total_purchase_cost, 0)) > 0 THEN 'Profitable'
        WHEN COALESCE(pr.total_revenue, 0) = 0 THEN 'No Revenue'
        ELSE 'Loss-Making'
    END as profitability_status
FROM projects p
LEFT JOIN products prod ON p.id = prod.id  -- 简化映射
LEFT JOIN project_revenue pr ON prod.id = pr.product_id
LEFT JOIN project_labor_cost plc ON p.id = plc.project_id
LEFT JOIN project_purchase_cost ppc ON p.id = ppc.project_id
WHERE p.archived = false;


-- 2. 里程碑交付与回款健康度 (Milestone-Payment Health)
-- 作用：监控技术交付进度与财务回款节奏的同步性
CREATE OR REPLACE VIEW view_finance_milestone_payment_health AS
SELECT 
    rc.contract_no,
    rc.title as contract_title,
    cpn.node_name as payment_node,
    cpn.billing_amount,
    m.title as linked_milestone,
    m.due_date as milestone_due_date,
    m.state as milestone_state,
    cpn.is_achieved as payment_achieved,
    cpn.achieved_at as payment_achieved_at,
    -- 交付-回款延迟（天数）
    CASE 
        WHEN cpn.achieved_at IS NOT NULL AND m.due_date IS NOT NULL THEN
            EXTRACT(DAY FROM (cpn.achieved_at - m.due_date))
        ELSE NULL
    END as delivery_payment_lag_days,
    -- 健康度状态
    CASE 
        WHEN cpn.is_achieved = true AND m.state = 'closed' THEN 'Healthy: Delivered & Paid'
        WHEN cpn.is_achieved = false AND m.state = 'closed' THEN 'Risk: Delivered but Unpaid'
        WHEN cpn.is_achieved = false AND m.due_date < CURRENT_DATE THEN 'Critical: Overdue Milestone'
        WHEN cpn.is_achieved = false AND m.state = 'active' THEN 'In Progress'
        ELSE 'Pending'
    END as payment_health_status
FROM contract_payment_nodes cpn
JOIN revenue_contracts rc ON cpn.contract_id = rc.id
LEFT JOIN milestones m ON cpn.linked_milestone_id = m.id
WHERE cpn.linked_system = 'gitlab'
ORDER BY 
    CASE 
        WHEN cpn.is_achieved = false AND m.due_date < CURRENT_DATE THEN 1
        WHEN cpn.is_achieved = false AND m.state = 'closed' THEN 2
        ELSE 3
    END,
    cpn.billing_amount DESC;


-- 3. 人力成本燃烧率与预算预警 (Burn Rate & Budget Alert)
-- 作用：监控项目的人力成本消耗速度与预算健康度
CREATE OR REPLACE VIEW view_finance_burn_rate_alert AS
WITH monthly_cost AS (
    SELECT 
        jp.gitlab_project_id as project_id,
        TO_CHAR(ji.updated_at, 'YYYY-MM') as month_str,
        SUM((ji.time_spent / 3600.0) * COALESCE(lrc.hourly_rate, 0)) as monthly_labor_cost
    FROM jira_issues ji
    JOIN jira_projects jp ON ji.project_id = jp.id
    LEFT JOIN users u ON ji.assignee_user_id = u.id
    LEFT JOIN labor_rate_configs lrc ON u.job_title_level = lrc.job_title_level AND lrc.is_active = true
    WHERE ji.time_spent > 0
      AND ji.updated_at >= NOW() - INTERVAL '6 months'
    GROUP BY jp.gitlab_project_id, TO_CHAR(ji.updated_at, 'YYYY-MM')
),
project_budget AS (
    SELECT 
        prod.id as product_id,
        SUM(rc.total_value) * 0.7 as estimated_budget  -- 假设70%为成本预算
    FROM revenue_contracts rc
    JOIN products prod ON rc.product_id = prod.id
    GROUP BY prod.id
)
SELECT 
    p.name as project_name,
    -- 累计已消耗成本
    SUM(mc.monthly_labor_cost) as total_spent,
    -- 预算基准
    COALESCE(pb.estimated_budget, 0) as total_budget,
    -- 月均燃烧率
    ROUND(AVG(mc.monthly_labor_cost), 2) as avg_monthly_burn_rate,
    -- 预算消耗率
    CASE 
        WHEN COALESCE(pb.estimated_budget, 0) > 0 THEN
            ROUND(SUM(mc.monthly_labor_cost) / pb.estimated_budget * 100, 2)
        ELSE 0
    END as budget_consumption_pct,
    -- 剩余预算
    COALESCE(pb.estimated_budget, 0) - SUM(mc.monthly_labor_cost) as remaining_budget,
    -- 跑道时长（月）
    CASE 
        WHEN AVG(mc.monthly_labor_cost) > 0 THEN
            ROUND((COALESCE(pb.estimated_budget, 0) - SUM(mc.monthly_labor_cost)) / AVG(mc.monthly_labor_cost), 1)
        ELSE NULL
    END as runway_months,
    -- 预警状态
    CASE 
        WHEN COALESCE(pb.estimated_budget, 0) = 0 THEN 'No Budget Defined'
        WHEN SUM(mc.monthly_labor_cost) / NULLIF(pb.estimated_budget, 0) > 0.9 THEN 'Critical: Budget Exhausted'
        WHEN SUM(mc.monthly_labor_cost) / NULLIF(pb.estimated_budget, 0) > 0.7 THEN 'Warning: High Consumption'
        ELSE 'Healthy'
    END as budget_alert_status
FROM projects p
LEFT JOIN monthly_cost mc ON p.id = mc.project_id
LEFT JOIN products prod ON p.id = prod.id
LEFT JOIN project_budget pb ON prod.id = pb.product_id
WHERE p.archived = false
GROUP BY p.name, pb.estimated_budget;


-- 4. 技术债务的财务量化 (Technical Debt Financial Impact)
-- 作用：将 SonarQube 的技术债务转换为财务成本
CREATE OR REPLACE VIEW view_finance_tech_debt_cost AS
WITH project_debt AS (
    SELECT 
        sp.gitlab_project_id as project_id,
        SUM(sm.sqale_index) / 60.0 as total_debt_hours,  -- 转换为小时
        SUM(sm.bugs) as total_bugs,
        SUM(sm.code_smells) as total_code_smells
    FROM sonar_projects sp
    JOIN sonar_measures sm ON sp.id = sm.project_id
    WHERE sm.analysis_date = (
        SELECT MAX(analysis_date) FROM sonar_measures WHERE project_id = sm.project_id
    )
    GROUP BY sp.gitlab_project_id
),
avg_hourly_rate AS (
    SELECT AVG(hourly_rate) as avg_rate
    FROM labor_rate_configs
    WHERE is_active = true
)
SELECT 
    p.name as project_name,
    g.name as group_name,
    ROUND(pd.total_debt_hours, 1) as debt_hours,
    -- 债务总额
    ROUND(pd.total_debt_hours * ahr.avg_rate, 2) as debt_cost,
    -- 债务密度（每千行代码的债务成本）
    CASE 
        WHEN sm.ncloc > 0 THEN
            ROUND((pd.total_debt_hours * ahr.avg_rate) / (sm.ncloc / 1000.0), 2)
        ELSE 0
    END as debt_density_per_kloc,
    pd.total_bugs,
    pd.total_code_smells,
    -- 债务等级
    CASE 
        WHEN pd.total_debt_hours * ahr.avg_rate > 100000 THEN 'Critical: Debt Black Hole'
        WHEN pd.total_debt_hours * ahr.avg_rate > 50000 THEN 'High: Significant Debt'
        WHEN pd.total_debt_hours * ahr.avg_rate > 10000 THEN 'Medium: Manageable Debt'
        ELSE 'Low: Healthy'
    END as debt_severity
FROM projects p
JOIN gitlab_groups g ON p.group_id = g.id
LEFT JOIN project_debt pd ON p.id = pd.project_id
LEFT JOIN sonar_projects sp ON p.id = sp.gitlab_project_id
LEFT JOIN sonar_measures sm ON sp.id = sm.project_id 
    AND sm.analysis_date = (SELECT MAX(analysis_date) FROM sonar_measures WHERE project_id = sm.project_id)
CROSS JOIN avg_hourly_rate ahr
WHERE p.archived = false
  AND pd.total_debt_hours IS NOT NULL
ORDER BY debt_cost DESC;


-- 5. 外包 vs 自研的成本效益分析 (Outsourcing vs In-house Cost-Benefit)
-- 作用：对比外包项目与自研项目的成本与质量
CREATE OR REPLACE VIEW view_finance_outsourcing_analysis AS
WITH project_classification AS (
    SELECT 
        p.id as project_id,
        p.name as project_name,
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM purchase_contracts pc 
                WHERE pc.vendor_name LIKE '%外包%' OR pc.vendor_name LIKE '%Outsourc%'
            ) THEN 'Outsourced'
            ELSE 'In-house'
        END as project_type
    FROM projects p
),
project_metrics AS (
    SELECT 
        jp.gitlab_project_id as project_id,
        SUM((ji.time_spent / 3600.0) * COALESCE(lrc.hourly_rate, 0)) as total_cost,
        COUNT(DISTINCT CASE WHEN ji.status IN ('Done', 'Closed') THEN ji.id END) as delivered_features,
        COUNT(DISTINCT CASE WHEN ji.issue_type = 'Bug' AND ji.labels::text LIKE '%reopened%' THEN ji.id END) as rework_count
    FROM jira_issues ji
    JOIN jira_projects jp ON ji.project_id = jp.id
    LEFT JOIN users u ON ji.assignee_user_id = u.id
    LEFT JOIN labor_rate_configs lrc ON u.job_title_level = lrc.job_title_level
    GROUP BY jp.gitlab_project_id
)
SELECT 
    pc.project_type,
    COUNT(DISTINCT pc.project_id) as project_count,
    -- 平均单位产出成本
    ROUND(AVG(pm.total_cost / NULLIF(pm.delivered_features, 0)), 2) as avg_cost_per_feature,
    -- 平均返工率
    ROUND(AVG(pm.rework_count::numeric / NULLIF(pm.delivered_features, 0) * 100), 2) as avg_rework_rate_pct,
    -- 质量调整成本
    ROUND(AVG(pm.total_cost * (1 + pm.rework_count::numeric / NULLIF(pm.delivered_features, 0))), 2) as quality_adjusted_cost,
    -- 成本效益评级
    CASE 
        WHEN pc.project_type = 'Outsourced' AND AVG(pm.total_cost / NULLIF(pm.delivered_features, 0)) > 
             (SELECT AVG(pm2.total_cost / NULLIF(pm2.delivered_features, 0)) FROM project_metrics pm2 
              JOIN project_classification pc2 ON pm2.project_id = pc2.project_id WHERE pc2.project_type = 'In-house') * 1.2
        THEN 'Expensive: Consider In-house'
        WHEN pc.project_type = 'Outsourced' THEN 'Cost-Effective'
        ELSE 'Baseline'
    END as cost_benefit_status
FROM project_classification pc
JOIN project_metrics pm ON pc.project_id = pm.project_id
GROUP BY pc.project_type;


-- 6. 研发资本化合规性监控 (R&D Capitalization Compliance)
-- 作用：识别可资本化的研发投入，确保会计合规
CREATE OR REPLACE VIEW view_finance_capex_compliance AS
WITH issue_classification AS (
    SELECT 
        jp.gitlab_project_id as project_id,
        ji.id as issue_id,
        ji.time_spent / 3600.0 as spent_hours,
        CASE 
            WHEN ji.labels::text LIKE '%Feature%' OR ji.labels::text LIKE '%Epic%' THEN 'CAPEX'
            WHEN ji.labels::text LIKE '%Bug%' OR ji.labels::text LIKE '%Refactor%' THEN 'OPEX'
            ELSE 'OPEX'  -- 默认费用化
        END as accounting_category
    FROM jira_issues ji
    JOIN jira_projects jp ON ji.project_id = jp.id
    WHERE ji.time_spent > 0
),
project_capex_summary AS (
    SELECT 
        project_id,
        SUM(CASE WHEN accounting_category = 'CAPEX' THEN spent_hours ELSE 0 END) as capex_hours,
        SUM(spent_hours) as total_hours
    FROM issue_classification
    GROUP BY project_id
)
SELECT 
    p.name as project_name,
    ROUND(pcs.capex_hours, 1) as capitalized_hours,
    ROUND(pcs.total_hours, 1) as total_hours,
    -- 资本化率
    ROUND(pcs.capex_hours / NULLIF(pcs.total_hours, 0) * 100, 2) as capitalization_rate_pct,
    -- 资本化金额
    ROUND(pcs.capex_hours * (SELECT AVG(hourly_rate) FROM labor_rate_configs WHERE is_active = true), 2) as capitalized_amount,
    -- 合规性评估
    CASE 
        WHEN pcs.capex_hours / NULLIF(pcs.total_hours, 0) < 0.3 THEN 'Low Risk: Conservative'
        WHEN pcs.capex_hours / NULLIF(pcs.total_hours, 0) BETWEEN 0.3 AND 0.7 THEN 'Compliant: Reasonable'
        WHEN pcs.capex_hours / NULLIF(pcs.total_hours, 0) > 0.7 THEN 'High Risk: Aggressive'
        ELSE 'No Data'
    END as compliance_status
FROM projects p
LEFT JOIN project_capex_summary pcs ON p.id = pcs.project_id
WHERE p.archived = false
  AND pcs.total_hours > 0
ORDER BY capitalization_rate_pct DESC;

-- ============================================================
-- Compliance & Internal Control Analytics Views
-- 此脚本用于创建内控与合规性视角的分析视图
-- 包含：四眼原则、权限滥用、变更追溯、敏感数据访问、职责分离、开源许可证、知识产权保护
-- ============================================================

-- 1. 四眼原则合规性监控 (Four-Eyes Principle Compliance)
-- 作用：确保代码合并经过独立审查，满足 SOX 404 职责分离要求
CREATE OR REPLACE VIEW view_compliance_four_eyes_principle AS
WITH mr_review_analysis AS (
    SELECT 
        mr.id as mr_id,
        mr.iid,
        mr.project_id,
        mr.title,
        mr.author_id,
        mr.state,
        mr.merged_at,
        mr.approval_count,
        -- 识别自审（作者在评论中参与审批）
        COUNT(DISTINCT CASE 
            WHEN n.author_id != mr.author_id AND n.system = false 
            THEN n.author_id 
        END) as independent_reviewers,
        -- 检查是否有实质性评审（非系统消息的评论）
        COUNT(CASE WHEN n.system = false THEN 1 END) as human_comments
    FROM merge_requests mr
    LEFT JOIN notes n ON mr.id = n.noteable_iid 
        AND mr.project_id = n.project_id 
        AND n.noteable_type = 'MergeRequest'
    WHERE mr.created_at >= NOW() - INTERVAL '90 days'
    GROUP BY mr.id, mr.iid, mr.project_id, mr.title, mr.author_id, mr.state, mr.merged_at, mr.approval_count
)
SELECT 
    p.name as project_name,
    g.name as group_name,
    COUNT(mra.mr_id) as total_merged_mrs,
    -- 零审批（直接合并）
    SUM(CASE WHEN mra.independent_reviewers = 0 AND mra.state = 'merged' THEN 1 ELSE 0 END) as zero_review_count,
    -- 单人审批
    SUM(CASE WHEN mra.independent_reviewers = 1 AND mra.state = 'merged' THEN 1 ELSE 0 END) as single_reviewer_count,
    -- 合规审批（≥2人）
    SUM(CASE WHEN mra.independent_reviewers >= 2 AND mra.state = 'merged' THEN 1 ELSE 0 END) as compliant_review_count,
    -- 零审批率
    ROUND(SUM(CASE WHEN mra.independent_reviewers = 0 AND mra.state = 'merged' THEN 1 ELSE 0 END)::numeric 
          / NULLIF(COUNT(CASE WHEN mra.state = 'merged' THEN 1 END), 0) * 100, 2) as zero_review_rate_pct,
    -- 合规率
    ROUND(SUM(CASE WHEN mra.independent_reviewers >= 2 AND mra.state = 'merged' THEN 1 ELSE 0 END)::numeric 
          / NULLIF(COUNT(CASE WHEN mra.state = 'merged' THEN 1 END), 0) * 100, 2) as compliance_rate_pct,
    -- 合规状态
    CASE 
        WHEN SUM(CASE WHEN mra.independent_reviewers = 0 AND mra.state = 'merged' THEN 1 ELSE 0 END)::numeric 
             / NULLIF(COUNT(CASE WHEN mra.state = 'merged' THEN 1 END), 0) > 0.2 
        THEN 'Critical: High Bypass Rate'
        WHEN SUM(CASE WHEN mra.independent_reviewers >= 2 AND mra.state = 'merged' THEN 1 ELSE 0 END)::numeric 
             / NULLIF(COUNT(CASE WHEN mra.state = 'merged' THEN 1 END), 0) < 0.5 
        THEN 'Warning: Low Compliance'
        ELSE 'Compliant'
    END as compliance_status
FROM mr_review_analysis mra
JOIN projects p ON mra.project_id = p.id
JOIN gitlab_groups g ON p.group_id = g.id
WHERE p.archived = false
GROUP BY p.name, g.name
ORDER BY zero_review_rate_pct DESC;


-- 2. 权限滥用与异常操作检测 (Privilege Abuse Detection)
-- 作用：识别非工作时间的敏感操作和权限滥用行为
CREATE OR REPLACE VIEW view_compliance_privilege_abuse AS
WITH off_hours_deployments AS (
    SELECT 
        project_id,
        COUNT(*) as total_deployments,
        SUM(CASE 
            WHEN EXTRACT(HOUR FROM created_at) >= 22 OR EXTRACT(HOUR FROM created_at) < 8 
                 OR EXTRACT(ISODOW FROM created_at) IN (6, 7)
            THEN 1 ELSE 0 
        END) as off_hours_deployments
    FROM deployments
    WHERE environment = 'production'
      AND created_at >= NOW() - INTERVAL '90 days'
    GROUP BY project_id
),
high_privilege_operations AS (
    SELECT 
        ggm.group_id,
        ggm.user_id,
        ggm.access_level,
        COUNT(DISTINCT c.id) as direct_commits
    FROM gitlab_group_members ggm
    JOIN users u ON ggm.user_id = u.id
    JOIN commits c ON u.id = c.gitlab_user_id
    WHERE ggm.access_level >= 40  -- Maintainer or Owner
      AND c.committed_date >= NOW() - INTERVAL '90 days'
    GROUP BY ggm.group_id, ggm.user_id, ggm.access_level
)
SELECT 
    p.name as project_name,
    g.name as group_name,
    COALESCE(ohd.total_deployments, 0) as total_prod_deployments,
    COALESCE(ohd.off_hours_deployments, 0) as off_hours_deployments,
    -- 非工作时间部署率
    ROUND(COALESCE(ohd.off_hours_deployments, 0)::numeric 
          / NULLIF(ohd.total_deployments, 0) * 100, 2) as off_hours_deployment_rate_pct,
    -- 超级管理员直接操作频率
    (SELECT COUNT(*) FROM high_privilege_operations hpo 
     WHERE hpo.group_id = g.id AND hpo.access_level = 50) as owner_direct_commits,
    -- 风险评级
    CASE 
        WHEN COALESCE(ohd.off_hours_deployments, 0)::numeric / NULLIF(ohd.total_deployments, 0) > 0.3 
        THEN 'High Risk: Frequent Off-Hours Operations'
        WHEN COALESCE(ohd.off_hours_deployments, 0)::numeric / NULLIF(ohd.total_deployments, 0) > 0.1 
        THEN 'Medium Risk: Some Off-Hours Operations'
        ELSE 'Low Risk'
    END as risk_level
FROM projects p
JOIN gitlab_groups g ON p.group_id = g.id
LEFT JOIN off_hours_deployments ohd ON p.id = ohd.project_id
WHERE p.archived = false
ORDER BY off_hours_deployment_rate_pct DESC;


-- 3. 变更管理合规性追溯 (Change Management Traceability)
-- 作用：确保生产变更可追溯到需求，满足 ITIL 变更管理要求
CREATE OR REPLACE VIEW view_compliance_change_traceability AS
WITH production_deployments AS (
    SELECT 
        d.id as deployment_id,
        d.project_id,
        d.ref,
        d.created_at,
        d.status,
        -- 尝试关联到 MR
        mr.id as linked_mr_id,
        mr.title as mr_title
    FROM deployments d
    LEFT JOIN merge_requests mr ON d.project_id = mr.project_id 
        AND d.ref LIKE '%' || mr.source_branch || '%'
    WHERE d.environment = 'production'
      AND d.created_at >= NOW() - INTERVAL '90 days'
),
mr_issue_links AS (
    SELECT 
        mr.id as mr_id,
        COUNT(DISTINCT tl.target_id) as linked_issues_count
    FROM merge_requests mr
    LEFT JOIN traceability_links tl ON CAST(mr.id AS TEXT) = tl.source_id 
        AND tl.source_system = 'gitlab' 
        AND tl.target_system = 'jira'
    GROUP BY mr.id
)
SELECT 
    p.name as project_name,
    COUNT(pd.deployment_id) as total_deployments,
    -- 可追溯到 MR
    SUM(CASE WHEN pd.linked_mr_id IS NOT NULL THEN 1 ELSE 0 END) as traceable_to_mr,
    -- 可追溯到 Issue
    SUM(CASE WHEN mil.linked_issues_count > 0 THEN 1 ELSE 0 END) as traceable_to_issue,
    -- 紧急变更（ref 包含 hotfix）
    SUM(CASE WHEN pd.ref LIKE '%hotfix%' OR pd.ref LIKE '%emergency%' THEN 1 ELSE 0 END) as emergency_changes,
    -- 未授权变更（无 MR 也无 Issue）
    SUM(CASE WHEN pd.linked_mr_id IS NULL THEN 1 ELSE 0 END) as unauthorized_changes,
    -- 可追溯率
    ROUND(SUM(CASE WHEN pd.linked_mr_id IS NOT NULL THEN 1 ELSE 0 END)::numeric 
          / NULLIF(COUNT(pd.deployment_id), 0) * 100, 2) as traceability_rate_pct,
    -- 合规状态
    CASE 
        WHEN SUM(CASE WHEN pd.linked_mr_id IS NULL THEN 1 ELSE 0 END)::numeric 
             / NULLIF(COUNT(pd.deployment_id), 0) > 0.2 
        THEN 'Non-Compliant: High Unauthorized Changes'
        WHEN SUM(CASE WHEN pd.linked_mr_id IS NOT NULL THEN 1 ELSE 0 END)::numeric 
             / NULLIF(COUNT(pd.deployment_id), 0) >= 0.9 
        THEN 'Compliant'
        ELSE 'Partially Compliant'
    END as compliance_status
FROM production_deployments pd
JOIN projects p ON pd.project_id = p.id
LEFT JOIN mr_issue_links mil ON pd.linked_mr_id = mil.mr_id
WHERE p.archived = false
GROUP BY p.name
ORDER BY traceability_rate_pct ASC;


-- 4. 敏感数据访问审计 (Sensitive Data Access Audit)
-- 作用：监控敏感文件的访问和变更，满足 GDPR/PIPL 数据保护要求
CREATE OR REPLACE VIEW view_compliance_sensitive_data_access AS
WITH sensitive_file_changes AS (
    SELECT 
        c.id as commit_id,
        c.project_id,
        c.gitlab_user_id,
        c.committed_date,
        cfs.file_path,
        cfs.code_added + cfs.code_added as total_changes,
        CASE 
            WHEN cfs.file_path LIKE '%config%' OR cfs.file_path LIKE '%secret%' 
                 OR cfs.file_path LIKE '%credential%' OR cfs.file_path LIKE '%password%'
                 OR cfs.file_path LIKE '%.env%' OR cfs.file_path LIKE '%key%'
            THEN 'Sensitive'
            ELSE 'Normal'
        END as file_sensitivity
    FROM commits c
    JOIN commit_file_stats cfs ON c.id = cfs.commit_id
    WHERE c.committed_date >= NOW() - INTERVAL '90 days'
)
SELECT 
    p.name as project_name,
    u.name as user_name,
    u.email as user_email,
    COUNT(DISTINCT sfc.commit_id) as total_commits,
    COUNT(DISTINCT CASE WHEN sfc.file_sensitivity = 'Sensitive' THEN sfc.commit_id END) as sensitive_file_commits,
    -- 敏感文件变更率
    ROUND(COUNT(DISTINCT CASE WHEN sfc.file_sensitivity = 'Sensitive' THEN sfc.commit_id END)::numeric 
          / NULLIF(COUNT(DISTINCT sfc.commit_id), 0) * 100, 2) as sensitive_change_rate_pct,
    -- 最近一次敏感操作
    MAX(CASE WHEN sfc.file_sensitivity = 'Sensitive' THEN sfc.committed_date END) as last_sensitive_access,
    -- 风险评级
    CASE 
        WHEN COUNT(DISTINCT CASE WHEN sfc.file_sensitivity = 'Sensitive' THEN sfc.commit_id END) > 10 
        THEN 'High Risk: Frequent Sensitive Access'
        WHEN COUNT(DISTINCT CASE WHEN sfc.file_sensitivity = 'Sensitive' THEN sfc.commit_id END) > 3 
        THEN 'Medium Risk'
        WHEN COUNT(DISTINCT CASE WHEN sfc.file_sensitivity = 'Sensitive' THEN sfc.commit_id END) > 0 
        THEN 'Low Risk'
        ELSE 'No Sensitive Access'
    END as risk_level
FROM sensitive_file_changes sfc
JOIN projects p ON sfc.project_id = p.id
JOIN users u ON sfc.gitlab_user_id = u.id
WHERE p.archived = false
GROUP BY p.name, u.name, u.email
HAVING COUNT(DISTINCT CASE WHEN sfc.file_sensitivity = 'Sensitive' THEN sfc.commit_id END) > 0
ORDER BY sensitive_file_commits DESC;


-- 5. 职责分离有效性验证 (Segregation of Duties - SoD)
-- 作用：确保同一人不同时拥有开发和发布权限，满足 SOX 404 要求
CREATE OR REPLACE VIEW view_compliance_segregation_of_duties AS
WITH user_roles AS (
    SELECT 
        u.id as user_id,
        u.name,
        u.email,
        -- 开发角色（有提交记录）
        CASE WHEN EXISTS (
            SELECT 1 FROM commits c WHERE c.gitlab_user_id = u.id 
            AND c.committed_date >= NOW() - INTERVAL '90 days'
        ) THEN true ELSE false END as is_developer,
        -- 发布角色（有生产部署记录）
        CASE WHEN EXISTS (
            SELECT 1 FROM deployments d 
            JOIN projects p ON d.project_id = p.id
            WHERE d.environment = 'production'
            AND d.created_at >= NOW() - INTERVAL '90 days'
            -- 假设部署者信息存储在某个字段，这里简化处理
        ) THEN true ELSE false END as is_deployer,
        -- 高权限角色
        CASE WHEN EXISTS (
            SELECT 1 FROM gitlab_group_members ggm 
            WHERE ggm.user_id = u.id AND ggm.access_level >= 40
        ) THEN true ELSE false END as has_high_privilege
    FROM users u
    WHERE u.state = 'active'
),
sod_violations AS (
    SELECT 
        user_id,
        name,
        email,
        is_developer,
        is_deployer,
        has_high_privilege,
        -- SoD 违规判定
        CASE 
            WHEN is_developer = true AND is_deployer = true THEN 'SoD Violation: Dev + Deploy'
            WHEN is_developer = true AND has_high_privilege = true THEN 'Potential Risk: Dev + Admin'
            ELSE 'Compliant'
        END as sod_status
    FROM user_roles
)
SELECT 
    name,
    email,
    is_developer,
    is_deployer,
    has_high_privilege,
    sod_status,
    -- 风险等级
    CASE 
        WHEN sod_status LIKE 'SoD Violation%' THEN 'Critical'
        WHEN sod_status LIKE 'Potential Risk%' THEN 'Medium'
        ELSE 'Low'
    END as risk_level
FROM sod_violations
WHERE sod_status != 'Compliant'
ORDER BY 
    CASE 
        WHEN sod_status LIKE 'SoD Violation%' THEN 1
        WHEN sod_status LIKE 'Potential Risk%' THEN 2
        ELSE 3
    END;


-- 6. 开源许可证合规性扫描 (Open Source License Compliance)
-- 作用：识别高风险开源许可证，降低知识产权诉讼风险
CREATE OR REPLACE VIEW view_compliance_oss_license_risk AS
WITH dependency_analysis AS (
    SELECT 
        gd.project_id,
        gd.name as package_name,
        gd.version,
        gd.package_manager,
        -- 简化的许可证风险判定（实际需要外部 API 查询）
        CASE 
            WHEN gd.name LIKE '%gpl%' THEN 'GPL (High Risk)'
            WHEN gd.name LIKE '%agpl%' THEN 'AGPL (Critical Risk)'
            WHEN gd.name LIKE '%lgpl%' THEN 'LGPL (Medium Risk)'
            WHEN gd.name LIKE '%apache%' THEN 'Apache (Low Risk)'
            WHEN gd.name LIKE '%mit%' THEN 'MIT (Low Risk)'
            ELSE 'Unknown License'
        END as license_risk
    FROM gitlab_dependencies gd
)
SELECT 
    p.name as project_name,
    COUNT(da.package_name) as total_dependencies,
    COUNT(CASE WHEN da.license_risk LIKE '%Critical%' THEN 1 END) as critical_risk_count,
    COUNT(CASE WHEN da.license_risk LIKE '%High%' THEN 1 END) as high_risk_count,
    COUNT(CASE WHEN da.license_risk = 'Unknown License' THEN 1 END) as unknown_license_count,
    -- 高风险许可证占比
    ROUND(COUNT(CASE WHEN da.license_risk LIKE '%Critical%' OR da.license_risk LIKE '%High%' THEN 1 END)::numeric 
          / NULLIF(COUNT(da.package_name), 0) * 100, 2) as high_risk_rate_pct,
    -- 合规状态
    CASE 
        WHEN COUNT(CASE WHEN da.license_risk LIKE '%Critical%' THEN 1 END) > 0 
        THEN 'Critical: AGPL Detected'
        WHEN COUNT(CASE WHEN da.license_risk LIKE '%High%' THEN 1 END) > 5 
        THEN 'High Risk: Multiple GPL'
        WHEN COUNT(CASE WHEN da.license_risk = 'Unknown License' THEN 1 END)::numeric 
             / NULLIF(COUNT(da.package_name), 0) > 0.3 
        THEN 'Warning: Many Unknown Licenses'
        ELSE 'Low Risk'
    END as compliance_status
FROM dependency_analysis da
JOIN projects p ON da.project_id = p.id
WHERE p.archived = false
GROUP BY p.name
ORDER BY critical_risk_count DESC, high_risk_count DESC;


-- 7. 代码归属与知识产权保护 (Code Ownership & IP Protection)
-- 作用：识别离职员工的异常行为和潜在的知识产权流失风险
CREATE OR REPLACE VIEW view_compliance_ip_protection AS
WITH user_activity_analysis AS (
    SELECT 
        u.id as user_id,
        u.name,
        u.email,
        u.state,
        -- 最近 30 天的提交量
        COUNT(DISTINCT CASE 
            WHEN c.committed_date >= NOW() - INTERVAL '30 days' THEN c.id 
        END) as commits_last_30_days,
        -- 最近 90 天的提交量
        COUNT(DISTINCT CASE 
            WHEN c.committed_date >= NOW() - INTERVAL '90 days' THEN c.id 
        END) as commits_last_90_days,
        -- 大规模删除
        SUM(CASE WHEN cfs.code_added < -1000 THEN 1 ELSE 0 END) as large_deletions,
        -- 外部邮箱提交
        COUNT(CASE WHEN c.author_email NOT LIKE '%@company.com%' THEN 1 END) as external_email_commits,
        MAX(c.committed_date) as last_commit_date
    FROM users u
    LEFT JOIN commits c ON u.id = c.gitlab_user_id
    LEFT JOIN commit_file_stats cfs ON c.id = cfs.commit_id
    WHERE c.committed_date >= NOW() - INTERVAL '90 days'
    GROUP BY u.id, u.name, u.email, u.state
)
SELECT 
    name,
    email,
    state,
    commits_last_30_days,
    commits_last_90_days,
    large_deletions,
    external_email_commits,
    last_commit_date,
    -- 异常活动检测
    CASE 
        WHEN state = 'inactive' AND commits_last_30_days > commits_last_90_days * 0.5 
        THEN 'Critical: High Activity Before Departure'
        WHEN large_deletions > 3 
        THEN 'High Risk: Multiple Large Deletions'
        WHEN external_email_commits > 5 
        THEN 'Medium Risk: External Email Usage'
        ELSE 'Normal'
    END as ip_risk_status,
    -- 风险等级
    CASE 
        WHEN state = 'inactive' AND commits_last_30_days > commits_last_90_days * 0.5 THEN 'Critical'
        WHEN large_deletions > 3 THEN 'High'
        WHEN external_email_commits > 5 THEN 'Medium'
        ELSE 'Low'
    END as risk_level
FROM user_activity_analysis
WHERE commits_last_90_days > 0
  AND (state = 'inactive' 
       OR large_deletions > 0 
       OR external_email_commits > 0
       OR commits_last_30_days > commits_last_90_days * 0.3)
ORDER BY 
    CASE 
        WHEN state = 'inactive' AND commits_last_30_days > commits_last_90_days * 0.5 THEN 1
        WHEN large_deletions > 3 THEN 2
        ELSE 3
    END,
    commits_last_30_days DESC;

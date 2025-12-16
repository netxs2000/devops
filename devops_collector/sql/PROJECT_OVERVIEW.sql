-- ============================================================
-- 视图名称: view_project_overview (项目全景概览 V6)
-- 更新日期: 2025-12-16
-- 
-- [功能描述]
-- 该视图是 DevOps 系统的核心数据资产，汇集了 GitLab (工程/需求) 和 SonarQube (质量) 的全量数据。
-- 它旨在为 PMO、项目经理和 Tech Lead 提供一个“上帝视角”，用于监控项目健康度、成本投入和交付风险。
--
-- [包含维度]
-- 1. 基础元数据 (Identity): 项目名称、URL、分支、归档状态
-- 2. 资产属性 (Assets): 可见性、仓库体积、关注度(Star)、复用度(Fork)
-- 3. 研发产出 (Output): 活跃天数、活跃率、代码提交量、人均产出
-- 4. 需求进度 (Progress): Issue 完成率、里程碑状态
-- 5. 成本管理 (Cost): 预估工时 vs 实际工时 (工时偏差分析)
-- 6. 质量风险 (Quality): Bug数、漏洞数、覆盖率、质量门禁 (SonarQube)
-- 7. 交付状态 (Delivery): 最新版本号、最近发版时间、流水线构建状态
-- 8. 团队贡献 (Team): 贡献者名单、最后责任人
-- ============================================================

CREATE OR REPLACE VIEW view_project_overview AS
WITH base_stats AS (
    -- [模块 1: 基础活动统计]
    -- 作用: 聚合 Commits 表，计算最基础的活跃指标
    SELECT 
        p.id as project_id,
        -- 计算项目年龄(天)，防止除以0错误
        GREATEST(1, EXTRACT(DAY FROM NOW() - p.created_at)) as project_age_days,
        -- 总提交次数
        COUNT(c.id) as total_commits,
        -- 活跃天数 (按日期去重)
        COUNT(DISTINCT DATE(c.committed_date)) as active_days,
        -- 参与贡献的人数
        COUNT(DISTINCT c.author_email) as author_count,
        -- 获取最后一次提交的作者 (Last Committer)
        (ARRAY_AGG(c.author_name ORDER BY c.committed_date DESC))[1] as last_committer
    FROM projects p
    LEFT JOIN commits c ON p.id = c.project_id
    GROUP BY p.id
),
mr_stats AS (
    -- [模块 2: 代码评审 (MR) 漏斗]
    -- 作用: 监控代码合并的吞吐量和阻塞情况
    SELECT 
        project_id,
        COUNT(*) as total_mrs,
        -- 积压的 MR (Open 状态)，反映评审瓶颈
        SUM(CASE WHEN state = 'opened' THEN 1 ELSE 0 END) as open_mrs,
        -- 已合并 MR，反映有效产出
        SUM(CASE WHEN state = 'merged' THEN 1 ELSE 0 END) as merged_mrs
    FROM merge_requests
    GROUP BY project_id
),
issue_stats AS (
    -- [模块 3: 需求进度与成本管理]
    -- 作用: 统计 Issue 完成情况及工时投入 (Time Tracking)
    SELECT 
        project_id,
        COUNT(*) as total_issues,
        SUM(CASE WHEN state = 'opened' THEN 1 ELSE 0 END) as open_issues,
        SUM(CASE WHEN state = 'closed' THEN 1 ELSE 0 END) as closed_issues,
        
        -- 工时统计 (数据库存储为秒，转换为小时)
        -- estimated_hours: 预估工时 (/estimate)
        ROUND(SUM(COALESCE(time_estimate, 0)) / 3600.0, 1) as total_estimated_hours,
        -- spent_hours: 实际消耗工时 (/spend)
        ROUND(SUM(COALESCE(total_time_spent, 0)) / 3600.0, 1) as total_spent_hours
    FROM issues
    GROUP BY project_id
),
sonar_stats AS (
    -- [模块 4: 代码质量与风险 (SonarQube)]
    -- 作用: 获取最新的代码扫描结果，识别质量风险
    SELECT 
        sp.gitlab_project_id,
        MAX(sm.files) as file_count,               -- 文件总数
        MAX(sm.ncloc) as ncloc,                    -- 有效代码行 (No Comment Lines of Code)
        MAX(sm.lines) as total_lines,              -- 物理总行数
        
        -- 注释率计算
        MAX(sm.comment_lines_density) as comment_density,
        -- 推算注释行数公式: (NCLOC * Density) / (100 - Density)
        ROUND((MAX(sm.ncloc) * MAX(sm.comment_lines_density)) / NULLIF(100 - MAX(sm.comment_lines_density), 0)) as est_comment_lines,
        
        -- 核心质量指标
        MAX(sm.bugs) as bug_count,                 -- Bug 数量 (可靠性)
        MAX(sm.vulnerabilities) as vulnerability_count, -- 漏洞数量 (安全性)
        MAX(sm.coverage) as coverage_pct,          -- 单元测试覆盖率
        MAX(sm.quality_gate_status) as quality_gate -- 质量门禁 (OK/WARN/ERROR)
    FROM sonar_projects sp
    JOIN sonar_measures sm ON sp.id = sm.project_id
    -- 仅取最近一次分析结果
    WHERE sm.analysis_date = (
        SELECT MAX(analysis_date) FROM sonar_measures WHERE project_id = sm.project_id
    )
    GROUP BY sp.gitlab_project_id
),
release_stats AS (
    -- [模块 5: 版本发布记录]
    -- 作用: 获取最近一次打 Tag 的信息，判断是否持续交付
    SELECT DISTINCT ON (project_id)
        project_id,
        name as last_tag_name,      -- 最新版本号 (例如 v1.2.0)
        created_at as last_release_at -- 发布时间
    FROM tags
    ORDER BY project_id, created_at DESC
),
milestone_stats AS (
    -- [模块 6: 迭代里程碑 (Milestones)]
    -- 作用: 识别当前正在进行的里程碑及其截止日期
    SELECT DISTINCT ON (project_id)
        project_id,
        title as active_milestone,    -- 当前里程碑名称
        due_date as milestone_due_date -- 截止日期 (Dead Line)
    FROM milestones
    WHERE state = 'active'
    ORDER BY project_id, due_date ASC -- 优先显示即将到期的
),
pipeline_stats AS (
    -- [模块 7: CI/CD 构建状态]
    -- 作用: 检查最近一次流水线是否跑通，识别构建阻断风险
    SELECT DISTINCT ON (project_id)
        project_id,
        status as last_pipeline_status, -- success, failed, running
        created_at as pipeline_at
    FROM pipelines
    ORDER BY project_id, created_at DESC
),
author_details AS (
    -- [模块 8: 团队贡献名单]
    -- 作用: 格式化生成 "姓名(提交数)" 字符串，直观展示谁是主力
    SELECT 
        project_id,
        STRING_AGG(formatted_name, ', ' ORDER BY commit_cnt DESC) as author_list_str
    FROM (
        SELECT 
            project_id,
            author_name || '(' || COUNT(*) || ')' as formatted_name,
            COUNT(*) as commit_cnt
        FROM commits
        GROUP BY project_id, author_name
        LIMIT 50 -- 限制显示前50名，防止字段过长
    ) t
    GROUP BY project_id
)

-- [主查询: 组装宽表]
SELECT 
    -- 1. [身份与元数据]
    g.name as group_name,                          -- 产品线/群组名称
    g.description as group_desc,                   -- 群组描述
    p.name as project_name,                        -- 项目名称
    p.description as project_desc,                 -- 项目描述
    p.web_url,                                     -- 项目跳转链接
    p.default_branch,                              -- 默认分支
    
    -- 2. [资产属性] (用于资产盘点)
    p.visibility,                                  -- 可见性 (public/people/private)
    p.archived,                                    -- 是否归档 (true=已废弃/封存)
    ROUND(p.storage_size / 1024.0 / 1024.0, 2) as storage_mb, -- 仓库体积 (MB)
    p.star_count,                                  -- 关注度 (Star)
    p.forks_count,                                 -- 复用度 (Fork)
    
    -- 3. [生命周期]
    p.created_at::date as creation_date,           -- 建立日期
    bs.project_age_days as age_days,               -- 项目年龄 (天)
    rs.last_release_at::date as last_release_date, -- 最近发版日
    rs.last_tag_name as last_version,              -- 最新版本号
    
    -- 4. [计划与里程碑]
    ms.active_milestone,                           -- 当前活跃里程碑
    ms.milestone_due_date,                         -- 里程碑截止日
    
    -- 5. [成本与进度] (PMO 关注核心)
    COALESCE(ist.total_issues, 0) as total_issues, -- 需求总数
    COALESCE(ist.open_issues, 0) as open_issues,   -- 未关闭需求数
    -- 需求完成率 (%)
    ROUND((COALESCE(ist.closed_issues, 0)::numeric / NULLIF(COALESCE(ist.total_issues, 0), 0)) * 100, 1) as issue_completion_pct,
    
    -- 工时成本 (Hours)
    COALESCE(ist.total_estimated_hours, 0) as estimated_hours, -- 预估工时
    COALESCE(ist.total_spent_hours, 0) as spent_hours,         -- 实际投入工时
    -- 工时偏差 (Variance): 正数=超支，负数=节约
    ROUND(COALESCE(ist.total_spent_hours, 0) - COALESCE(ist.total_estimated_hours, 0), 1) as time_variance_hours,
    
    -- 6. [研发吞吐量] (MR)
    COALESCE(mrs.total_mrs, 0) as total_mrs,       -- 累计 MR 数
    COALESCE(mrs.open_mrs, 0) as open_mrs_backlog, -- 积压 MR (评审瓶颈)
    COALESCE(mrs.merged_mrs, 0) as merged_mrs,     -- 已合并 MR (有效吞吐)
    
    -- 7. [质量与风险] (SonarQube)
    COALESCE(ss.bug_count, 0) as bugs,             -- Bug 数量
    COALESCE(ss.vulnerability_count, 0) as vulnerabilities, -- 漏洞数量
    COALESCE(ss.coverage_pct, 0) as coverage_pct,  -- 覆盖率 (%)
    COALESCE(ss.quality_gate, 'N/A') as quality_gate, -- 质量门禁 (ERROR即为高风险)
    COALESCE(pls.last_pipeline_status, 'N/A') as build_status, -- 构建状态

    -- 8. [工程产出] (活跃度分析)
    bs.active_days,                                -- 活跃天数
    -- 活跃率 (%): 活跃天 / 总天数，衡量项目是否持续迭代
    ROUND((bs.active_days::numeric / NULLIF(bs.project_age_days, 0)) * 100, 2) as active_rate_pct,
    bs.total_commits,                              -- 总提交数
    
    -- 平均产出效率
    ROUND(bs.total_commits::numeric / NULLIF(bs.active_days, 0)) as avg_daily_commits, -- 活跃天平均提交
    ROUND(bs.total_commits::numeric / NULLIF(bs.author_count, 0)) as avg_author_commits, -- 人均提交数
    
    -- 9. [代码规模]
    COALESCE(ss.file_count, 0) as file_count,      -- 文件总数
    COALESCE(ss.ncloc, 0) as code_lines,           -- 有效代码行
    COALESCE(ss.est_comment_lines, 0) as comment_lines, -- 注释行
    COALESCE(ss.comment_density, 0) as comment_pct, -- 注释率 (%)

    -- 10. [团队信息]
    bs.last_committer,                             -- 最后责任人
    COALESCE(ad.author_list_str, '') as contributors -- 贡献者名单

FROM projects p
JOIN gitlab_groups g ON p.group_id = g.id
LEFT JOIN base_stats bs ON p.id = bs.project_id
LEFT JOIN mr_stats mrs ON p.id = mrs.project_id
LEFT JOIN issue_stats ist ON p.id = ist.project_id 
LEFT JOIN sonar_stats ss ON p.id = ss.gitlab_project_id
LEFT JOIN release_stats rs ON p.id = rs.project_id
LEFT JOIN milestone_stats ms ON p.id = ms.project_id
LEFT JOIN pipeline_stats pls ON p.id = pls.project_id
LEFT JOIN author_details ad ON p.id = ad.project_id

ORDER BY g.name, p.name;

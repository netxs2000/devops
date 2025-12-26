# 团队效能视角 DevInsight 分析方案

本文档描述了如何基于 DevOps 数据（GitLab, SonarQube）构建**团队级 (Team/Squad/Department)** 的效能度量与分析体系。
旨在通过客观数据评估团队的交付效率、协作健康度、质量内建能力及架构债务情况。

## 1. 核心分析维度

| 分析维度 | 业务含义 | 数据来源 | 关键指标 | 作用与意义 |
| :--- | :--- | :--- | :--- | :--- |
### 1.1 交付效能 (Delivery Efficiency)
- **业务含义**: 响应速度与吞吐量
- **数据来源**: GitLab (MR/Pipeline)
- **关键指标**: **DORA 指标 (变更前置时间, 发布频率, MTTR)**, WIP (并行需求数), **项目活力 (Vitality)**
- **作用与意义**: 衡量团队对业务需求的响应速度；结合 `dept_performance.sql` 监控活跃项目占比，防止僵尸项目拖累资源。

### 1.2 质量内建 (Built-in Quality)
- **业务含义**: 交付物的可靠性
- **数据来源**: SonarQube + GitLab
- **关键指标**: **变更失败率**, **质量门禁通过率**, 逃逸缺陷密度, **幽灵分支 (Ghost Branches)**
- **作用与意义**: 评估团队是否做到了"一次把事情做对"；结合 `process_deviation.sql` 清理长期未合并的幽灵分支，降低维护噪音。

### 1.3 协作健康 (Collaboration Health)
- **业务含义**: 团队凝聚力与风险
- **数据来源**: GitLab (Notes/Commits)
- **关键指标**: **Review 参与度**, **Bus Factor (大巴指数)**, **评审乒乓指数 (Review Quality)**, **代码孤岛 (Silo Index)**: 统计文件修改者的集中度 (Bus Factor)。
- **作用与意义**: 识别"知识孤岛"风险；结合 `review_quality.sql` 区分"橡皮图章"式评审与有效评审，提升代码审查实效。

### 1.4 架构债务 (Architecture Health)
- **业务含义**: 长期可维护性
- **数据来源**: SonarQube
- **关键指标**: **技术债务总额**, **遗留代码比例**, 复杂度趋势
- **作用与意义**: 监控团队背负的"技术利息"增长情况，辅助架构重构决策。

### 1.5 流程合规 (Process & Compliance)
- **业务含义**: 研发规范执行力
- **数据来源**: GitLab Commits
- **关键指标**: **游离代码率 (Unmanaged Code)**, 提交信息规范度
- **作用与意义**: 衡量团队是否遵守研发规范（如关联 Issue ID）；参考 `process_deviation.sql` 发现"野路子"开发行为。

### 1.6 内源文化 (InnerSource & Culture)
- **业务含义**: 开放与共享
- **数据来源**: Cross-Project Commits
- **关键指标**: **内源贡献率 (InnerSource Rate)**, 跨团队协作占比
- **作用与意义**: 衡量团队的开放程度和跨部门影响力；参考 `innersource.sql` 识别打破部门墙的先锋团队。

---

## 2. BI 数据宽表设计 (SQL)

以下 SQL 脚本可直接在数据库执行，生成面向 BI 工具的团队级视图。建议结合第 4 章节的现有 SQL 资产进行组合使用。

### 2.1 团队 DORA 核心指标看板 (Team DORA Dashboard)
**SQL 视图**: `view_team_dora_metrics`

```sql
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
```

### 2.2 团队协作健康度 (Collaboration Health)
**SQL 视图**: `view_team_collaboration_health`

```sql
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
```

### 2.3 团队技术债务与质量 (Technical Debt & Quality)
**SQL 视图**: `view_team_quality_debt`

```sql
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
```

### 2.4 流程与文化健康度 (Process & Culture Health)

**作用**：综合评估团队的流程规范性和开放文化。
**关键指标**：游离代码率 (越高越差), 内源贡献率 (越高越好)。

```sql
CREATE OR REPLACE VIEW view_team_process_culture AS
WITH commit_stats AS (
    SELECT 
        p.id as project_id,
        COUNT(*) as total_commits,
        -- 游离代码: Message 中不包含 Issue ID (简单正则示例)
        COUNT(CASE WHEN c.title !~ '(#\d+|[A-Z]+-\d+)' THEN 1 END) as unmanaged_commits
    FROM commits c
    JOIN projects p ON c.project_id = p.id
    WHERE c.committed_date >= NOW() - INTERVAL '90 days'
    GROUP BY p.id
),
innersource_stats AS (
    -- 简化的内源贡献: 统计该团队成员向其他 Group 项目的提交 (需结合 User 归属)
    -- 此处仅为示例逻辑
    SELECT 
        g.id as group_id,
        COUNT(distinct c.id) as cross_contributions
    FROM gitlab_groups g
    JOIN gitlab_group_members gm ON g.id = gm.group_id
    JOIN users u ON gm.user_id = u.id
    JOIN commits c ON u.id = c.gitlab_user_id
    JOIN projects p ON c.project_id = p.id
    WHERE p.group_id != g.id -- 提交到了非本组项目
    AND c.committed_date >= NOW() - INTERVAL '90 days'
    GROUP BY g.id
)
SELECT 
    g.name as group_name,
    -- 流程合规
    ROUND(SUM(cs.unmanaged_commits)::numeric / NULLIF(SUM(cs.total_commits), 0) * 100, 1) as unmanaged_code_ratio_pct,
    
    -- 内源文化
    COALESCE(ins.cross_contributions, 0) as innersource_commits_count
    
FROM gitlab_groups g
JOIN projects p ON g.id = p.group_id
LEFT JOIN commit_stats cs ON p.id = cs.project_id
LEFT JOIN innersource_stats ins ON g.id = ins.group_id
GROUP BY g.name, ins.cross_contributions
ORDER BY unmanaged_code_ratio_pct ASC;
```

---

## 3. 现有 SQL 资产复用建议 (SQL Asset Reuse)

*(原内容保留，移至第 4 章)*

---

## 4. 现有 SQL 资产盘点 (SQL Asset Inventory)

为了确保分析逻辑的一致性和长期维护，以下列出项目中现有的 SQL 脚本资产及其在团队分析中的深度应用。

### 4.1 DORA 指标标准实现
**脚本路径**: `plugins/gitlab/sql_views/dora_metrics.sql`

- **核心逻辑**: 计算 Google DORA 四项核心指标：发布频率 (Deployment Frequency)、变更前置时间 (Lead Time)、变更失败率 (Change Failure Rate)、服务恢复时间 (MTTR)。
- **价值**: 提供业界公认的研发效能度量标准，帮助团队对标行业基线。
- **维度**: 交付效能 (Delivery Efficiency)
- **实现方式**:
    - **发布频率**: 统计 `deployments` 表中 environment 为生产环境且状态为 success 的记录数。
    - **前置时间**: 计算 `merge_requests` 表中 merged_at 与 created_at 的时间差。
    - **MTTR**: 统计 `issues` 表中 label 包含 'incident' 的工单从创建到关闭的时长。

### 4.2 评审质量深度透视
**脚本路径**: `plugins/gitlab/sql_views/review_quality.sql`

- **核心逻辑**: 统计 Merge Request 的交互轮次（"乒乓"次数），区分无效评审。
- **价值**: 识别形式主义的 Code Review（如秒过、无评论），确保代码审查真正发挥了质量门禁的作用。
- **维度**: 协作健康 (Collaboration Health)
- **实现方式**:
    - **乒乓指数**: 统计 MR 下非作者本人且非系统自动生成的 `notes` (评论) 数量。
    - **橡皮图章判定**: 如果一个 MR 的乒乓次数为 0 即合并，标记为 "Rubber Stamp"。

### 4.3 流程合规与风险监控
**脚本路径**: `plugins/gitlab/sql_views/process_deviation.sql`

- **核心逻辑**: 扫描不符合研发规范的操作，如 Commit Message 不规范、分支长期未合并。
- **价值**: 发现团队在流程执行上的短板，降低代码仓库的维护熵增，避免“野路子”开发带来的合规风险。
- **维度**: 流程合规 (Process & Compliance)
- **实现方式**:
    - **游离代码**: 正则匹配 `commits.title`，查找不包含 Issue ID (如 #123, PROJ-123) 的提交。
    - **幽灵分支**: 筛选 `branches` 表中最后提交时间 > 30 天且未合并的分支。

### 4.4 内源贡献与打破孤岛
**脚本路径**: `plugins/gitlab/sql_views/innersource.sql`

- **核心逻辑**: 统计跨项目、跨团队的代码提交行为，以及单人维护的高风险文件。
- **价值**: 鼓励技术共享和开源文化，识别并消除“知识孤岛” (Bus Factor 风险)。
- **维度**: 内源文化 (InnerSource & Culture)
- **实现方式**:
    - **内源贡献率**: 关联 `users` 所在部门与 `projects` 所属部门，统计跨部门提交占比。
    - **孤岛指数**: 聚合 `commit_file_stats`，找出 80% 代码由同一人提交的核心文件。

### 4.5 部门级资源宏观盘点
**脚本路径**: `plugins/gitlab/sql_views/dept_performance.sql`

- **核心逻辑**: 按组织架构 (Group/Deparment) 聚合统计资源消耗和活跃度。
- **价值**: 为 PMO 或管理层提供视角的宏观数据，识别资源浪费（僵尸项目）和投入产出比。
- **维度**: 交付效能 (Delivery Efficiency)
- **实现方式**:
    - **项目活力**: 统计最近 30 天有 commit/issue 活动的项目占比。
    - **资源规模**: 聚合计算仓库存储大小 `storage_size` 和人员规模。


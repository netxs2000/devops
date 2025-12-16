# 人力资源视角 DevInsight 分析方案

本文档描述了如何基于 DevOps 数据（GitLab, SonarQube）构建人力资源管理 (HRM) 分析体系。
旨在通过客观数据辅助：人员能力画像、高潜人才识别、培养发展、流失预警等管理动作。

## 1. 核心分析维度

### 1.1 产出 (Output)
- **业务含义**: 工作量与生产力
- **数据来源**: GitLab Commits
- **关键指标**: 提交次数, 代码增加行数, 有效代码产出, **活跃生命周期 (Tenure)**
- **作用与意义**: 衡量员工的基础工作产出，识别高效能与低效能员工；结合 `user_lifecycle.sql` 分析员工的稳定性与成长曲线。

### 1.2 影响 (Impact)
- **业务含义**: 技术推动力
- **数据来源**: GitLab MRs
- **关键指标**: 合并 MR 数, 解决 Issue 数, **救火次数 (发布后 Bug 修复)**
- **作用与意义**: 评估员工对项目的实际推动作用，识别核心贡献者；结合 `burnout_radar.sql` 中的冲刺后遗症指标，识别谁是团队的关键"救火队员"。

### 1.3 协作 (Collaboration)
- **业务含义**: 团队贡献与指导
- **数据来源**: GitLab Notes
- **关键指标**: Code Review 次数, 评论互动量, **平均每单评审数 (Review Depth)**
- **作用与意义**: 衡量员工的团队协作意愿和 Mentorship 能力，识别潜在的 Tech Lead。参考 `user_code_review.sql` 区分"点赞之交"与"深度评审"。

### 1.4 质量 (Quality)
- **业务含义**: 代码稳健性
- **数据来源**: SonarQube
- **关键指标**: 引入 Bug 数, 引入漏洞数, 制造技术债务
- **作用与意义**: 评估代码质量，识别需要改进的领域，防止低质量代码累积。
    参考'view_hr_user_capability_profile.sql'这个视图（能力雷达图）中包含了最基础的质量指标。在 'view_hr_user_quality_scorecard.sql' 中"个人代码质量计分卡"。

### 1.5 广度 (Breadth)
- **业务含义**: 技术栈覆盖面
- **数据来源**: Commit Stats
- **关键指标**: 掌握语言数量 (Polyglot), 跨项目贡献度, **技能树 (Skills List)**
- **作用与意义**: 识别 T 型人才（一专多能），发现团队技能短板，辅助人才培养。参考 `user_tech_stack.sql` 构建团队技能热力图。

### 1.6 投入 (Engagement)
- **业务含义**: 工作状态与风险
- **数据来源**: Commit Time
- **关键指标**: 活跃天数, 加班强度 (深夜/周末提交), **WLB 指数**, **流失状态 (Churned/Dormant)**
- **作用与意义**: 识别工作饱和度、潜在的职业倦怠风险和离职倾向。结合 `burnout_radar.sql` 和 `user_lifecycle.sql` 进行早期预警。

### 1.7 质量深挖 (Quality Deep Dive) - SonarQube 增强
- **业务含义**: 技能水平与责任心
- **数据来源**: SonarQube Issues
- **关键指标**:
    - **技术债务归因**: 个人引入的 Debt 总时长 (反映代码可维护性)。
    - **安全意识**: 引入的安全热点/漏洞数量 (反映安全编码能力)。
    - **误报反馈率**: 标记为 "False Positive" 的比例 (反映对业务逻辑的自信和判定能力)。
- **作用与意义**: 区分"快枪手"(产出高但质量差)与"工匠"(产出稳且质量高)，为技术培训提供精准输入。

---

## 2. BI 数据宽表设计 (SQL)

以下 SQL 脚本可直接在数据库执行，生成面向 BI 工具的视图。建议结合第 4 章节的现有 SQL 资产进行组合使用。

### 2.1 人员能力综合画像 (User Capability Profile)
**SQL 视图**: `view_hr_user_capability_profile`

```sql
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
```

### 2.2 技术栈分布雷达 (Tech Stack Radar)
**SQL 视图**: `view_hr_user_tech_stack`

```sql
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
```

### 2.3 人才流失风险预警 (Retention Risk Dashboard)
**SQL 视图**: `view_hr_retention_risk`

```sql
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
```

### 2.4 个人代码质量计分卡 (Personal Quality Scorecard)

**作用**：基于 SonarQube 问题数据，精确评估个人的代码质量表现。
**注意**：此视图依赖 `sonar_issues` 表中的 `author` 字段与 `users` 表的 `username` 或 `email` 进行关联，可能需要根据实际账号体系调整 JOIN 逻辑。

**SQL 视图**: `view_hr_user_quality_scorecard`

```sql
CREATE OR REPLACE VIEW view_hr_user_quality_scorecard AS
WITH issue_stats AS (
    SELECT 
        author,
        -- 严重问题统计
        COUNT(*) FILTER (WHERE severity IN ('BLOCKER', 'CRITICAL')) as critical_issues,
        COUNT(*) FILTER (WHERE type = 'VULNERABILITY') as vulnerabilities,
        COUNT(*) FILTER (WHERE type = 'BUG') as bugs,
        
        -- 技术债务 (简化计算：假设 effort 存储格式为分钟数或需清洗)
        -- 这里仅做计数示意，若 effort 为字符串需额外解析
        COUNT(*) FILTER (WHERE type = 'CODE_SMELL') as code_smells,
        
        -- 误报/被标记无效的数量 (推诿 vs 自信?)
        COUNT(*) FILTER (WHERE resolution IN ('FALSE-POSITIVE', 'WONTFIX')) as wonfix_issues
    FROM sonar_issues
    WHERE creation_date >= NOW() - INTERVAL '90 days'
    GROUP BY author
)
SELECT 
    u.name,
    u.department,
    COALESCE(s.critical_issues, 0) as metric_critical_issues,
    COALESCE(s.vulnerabilities, 0) as metric_security_vulns,
    COALESCE(s.wonfix_issues, 0) as metric_false_positives,
    
    -- 质量排名分 (示例算法: 100 - 严重问题x5 - 漏洞x10)
    GREATEST(0, 100 - (COALESCE(s.critical_issues, 0) * 5) - (COALESCE(s.vulnerabilities, 0) * 10)) as quality_score
    
FROM users u
JOIN issue_stats s ON u.username = s.author -- 关联关键点
WHERE u.state = 'active'
ORDER BY quality_score DESC;
```

---

## 3. 落地建议

1.  **数据隐私保护**：此类数据涉及员工隐私，建议在 BI 系统中设置严格的**行级权限控制 (Row Level Security)**，仅允许 HRBP 和 部门总监 查看对应部门数据。
2.  **避免单一指标考核**：以上数据仅作为辅助参考，**严禁**直接用于 KPI 考核（如“代码行数越多奖金越多”），否则会导致严重的刷数据行为（Goodhart 定律）。
3.  **结合线下沟通**：当系统发出“流失预警”时，应作为管理者发起 1:1 沟通的信号，而非直接认定员工有问题。

---

## 4. 现有 SQL 资产盘点 (SQL Asset Inventory)

为了确保分析逻辑的一致性和长期维护，以下列出项目中现有的 SQL 脚本资产及其在 HR 分析中的对应关系。建议复用这些逻辑而非重复造轮子。

| 脚本路径 | 核心功能 | HR 分析价值 | 对应维度 |
| :--- | :--- | :--- | :--- |
| `plugins/gitlab/sql_views/user_lifecycle.sql` | 计算用户首次/最后活跃时间、活跃天数、存留状态 | **司龄分析、流失状态判定** (Active/Dormant/Churned)。比单纯看最后活跃时间更精准。 | 投入 (Engagement) |
| `plugins/gitlab/sql_views/user_tech_stack.sql` | 聚合用户提交文件的语言分布，生成技能列表 | **技能盘点、T型人才识别**。可直接生成“掌握 3 门以上语言的员工”名单。 | 广度 (Breadth) |
| `plugins/gitlab/sql_views/user_code_review.sql` | 统计 Review 次数和深度 (平均评论数) | **Tech Lead 识别、导师能力评估**。区分“只是点 Merge”和“认真 Review 代码”的员工。 | 协作 (Collaboration) |
| `plugins/gitlab/sql_views/burnout_radar.sql` | 计算 WLB 指数、周末/深夜提交占比 | **加班强度监控、健康度预警**。提供了更精细的时间段判定逻辑。 | 投入 (Engagement) |
| `plugins/gitlab/sql_views/author_stats.sql` | 基础代码贡献统计 | **基础产出评估**。最基础的“搬砖”量统计。 | 产出 (Output) |


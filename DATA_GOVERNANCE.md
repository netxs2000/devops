# 数据治理白皮书 (Data Governance Whitepaper)

**版本**: 1.0.0  
**日期**: 2025-12-20

## 1. 治理愿景
确保 DevOps 效能平台产出的每一项指标都是**可信任、可审计、可回溯**的。数据不仅是图表，更是公司资产分摊与人员画像的法律依据。

## 2. 身份治理 (Identity Governance)

### 2.1 归一化原则
各系统（GitLab, Jira, Sonar, ZenTao, Jenkins）中的账号通过 `IdentityManager` 进行强校验：
*   **第一优先级**: Email (大小写不敏感匹配)。
*   **第二优先级**: 工号 (Employee ID)。
*   **辅助匹配**: 优先尝试解析 GitLab User Profile 中的 `skype` 字段获取中心归属。

### 2.2 跨系统项目对齐 (Project Alignment)
为了保证 DORA 和 ROI 的准确性，必须遵循以下命名/映射原则：
*   **Artifact -> Source**: 制品库中的 `GAV` (Group:Artifact:Version) 坐标必须能回溯至 GitLab 具体的 `Project_ID`。
*   **Jira -> GitLab**: 建议在 Jira Issue 中关联 GitLab Commit/MR。系统会自动解析 `issuelinks` 建立依赖阻塞血缘。
*   **禅道 -> 系统**: 系统自动同步禅道部门树并作为 `Organization` 的核心来源。

## 3. 指标治理 (Metrics Governance)

### 3.1 财务与人工成本治理
由于 `view_pmo_project_labor_costs` 直接关联核算：
*   **费率生效规则**: `labor_rate_configs` 必须按职级 (`job_title_level`) 完全覆盖当前活跃用户。
*   **工时偏差 (TV)**: 系统自动识别预估与实际工时的 30% 以上偏差，并作为“数据质量风险”推送至预警机器人。

### 3.2 AI 语义治理
*   **AI Category**: 定期人工抽检 5% 的 AI 自动分类结果。若准确率连续低于 80%，需更新 Prompt 模板或调整模型参数。

### 3.3 自动化归责逻辑 (Automated Attribution) 🌟
为了确保人员画像的公正性，系统遵循“谁产生，谁负责”的原则：
*   **Sonar 问题归责**: 实时读取 SonarQube SCM (Git Blame) 提供的 `author` 字段，通过身份中心映射至全局 `user_id`。
*   **代码规范 (Lint) 归责**: 采用“提交人负责制”。Commit 关联的 CI 流水线若 Lint 失败，则该作者的质量分相应扣减。
*   **Bug 归责**: 
    - **缺陷引入者**: 通过 `traceability_links` 追溯导致该缺陷的原始 MR/Commit 作者。
    - **缺陷修复者**: 归属于 Jira/禅道任务中的 `assignee`（经办人）。

### 3.2 异常数据处理
*   **空值补偿**: 若 Jira 未填预估时间，进度分析 (`completion_rate_pct`) 自动采用该项目同类型 Issue 的平均值进行估算，并标记“估算”状态。
*   **去噪逻辑**: 采集时自动过滤机器人账号（如 `gitlab-bot`）的活动，确保不干扰真实的开发效能数据。

## 4. 存储与保留政策 (Retention Policy)

### 4.1 原始数据 (Raw Data)
存储在 `raw_data_staging` 表中的原始 JSON：
*   **保留期**: 默认保留 30 天。
*   **价值**: 用于逻辑重演 (Replay) 和 Bug 修复后的数据回刷。

### 4.2 事实数据 (Fact Tables)
转换后的结构化数据：
*   **定期备份**: 每日进行物理备份。
*   **归档**: 超过 2 年的历史数据将迁移至归档库，保持生产库轻量。

## 5. 权限与隐私 (Security & Privacy)

*   **脱敏要求**: 任何导出的 Excel/PDF 报表严禁包含明文手机号。
*   **访问控制**: 
    *   **普通用户**: 仅可见个人及所属项目视图。
    *   **PMO/HR**: 可见部门汇总视图。
    *   **CTO**: 可见全量战略对齐视图。

# 用户接入与指标指南 (User & Metrics Guide)

## 1. 接入指南 (Onboarding Guide)

### 1.1 什么是 DevOps Data Collector?
这是一个自动化的效能数据采集平台，不需要您手动填报数据。只要您的项目在公司的 GitLab 上，且配置了 SonarQube，数据就会自动进入系统。

### 1.2 如何接入 GitLab 数据?
*   **自动发现**: 系统每天凌晨会自动扫描 GitLab 全量项目。
*   **归属确认**: 请确保您的 GitLab 项目位于正确的 **Group** 下。系统会根据 Group Description 自动将项目归属到对应的部门。

### 1.3 如何接入 SonarQube 数据?
为了让系统能自动关联 GitLab 代码库和 SonarQube 质量报告，请遵循以下命名规范：

*   **Sonar Project Key**: 必须与 GitLab 的 `Path with namespace` 一致（将 `/` 替换为 `:` 或保持一致，视具体配置而定）。
    *   *GitLab*: `infra/devops-platform`
    *   *Sonar*: `infra:devops-platform` (推荐)
*   如果无法遵循此规范，请联系管理员手动在数据库配置映射。

---

## 2. 指标白皮书 (Metrics Dictionary)

### 2.1 交付效能 (Delivery)

#### 🚀 部署频率 (Deployment Frequency)
*   **定义**: 单位时间内成功部署到生产环境的次数。
*   **数据源**: `deployments` 表。
*   **统计口径**: 仅统计 `status='success'` 且 `environment='production'` 的记录。

#### ⏱️ 变更前置时间 (Lead Time for Changes)
*   **定义**: 从代码提交 (Commit) 到代码成功运行在生产环境 (Deployment) 的时间。
*   **简化版口径**: 因通过 Commit 追踪太复杂，目前版本采用 **MR 合并耗时** (从 `created_at` 到 `merged_at`) 作为近似替代。

### 2.2 代码质量 (Quality)

#### 🌡️ 技术债务 (Technical Debt / SQALE)
*   **定义**: 修复代码中所有可维护性问题所需的预估时间。
*   **单位**: 分钟 (min)E
*   **解读**: 数值越低越好。如果该指标持续上升，说明团队在以牺牲代码质量为代价赶进度。

#### 🛡️ 代码覆盖率 (Code Coverage)
*   **定义**: 单元测试覆盖的代码行数比例。
*   **门禁**: 建议核心模块不低于 80%。

### 2.3 活跃度 (Activity)

#### 🧟 僵尸分支 (Zombie Branches)
*   **定义**: 超过 3 个月未合并且无新提交的分支。
*   **建议**: 定期清理，保持仓库整洁。

#### 💻 有效代码行 (Effective Lines of Code)
*   **数据源**: `commit_file_stats`
*   **计算**: `code_added` (仅计算实际代码，不含空行和注释)。
*   **用途**: 衡量工作量，但**严禁**直接用于绩效考核。

---

## 3. 常见问题 (FAQ)

### Q: 为什么我看不到我的 commit 数据?
A: 
1. 检查提交用的 Email 是否是公司邮箱。
2. 系统每小时同步一次，可能存在延迟。

### Q: 我是外部外包人员，没有公司邮箱怎么办?
A: 请联系管理员，将您的个人邮箱录入到 `sys_users` 表，并标记为虚拟账号，即可归并数据。

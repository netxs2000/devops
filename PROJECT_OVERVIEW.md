# 项目全景概览 (Project Comprehensive Overview)

## 1. 概述 (Overview)
**项目全景概览** 是一套基于 GitLab、SonarQube 和 Jenkins 数据的综合分析视图。它打破了单一工具的数据孤岛，将工程产出（GitLab）、代码质量（SonarQube）、构建效能（Jenkins）、项目进度（Issues/Milestones）和资源成本（Time Tracking）融合为一张“上帝视角”的大宽表。

该视图旨在为 PMO、项目经理、技术负责人提供一个**实时的、可量化的**项目健康体检报告。

## 2. 目的与意义 (Purpose & Value)

### 2.1 目的
- **填补视角空白**：解决以往只看代码提交量，不看需求完工率和质量风险的片面视角。
- **量化项目健康**：通过活跃率、工时偏差、质量门禁等复合指标，数字化定义什么是“健康的项目”。
- **资产盘点**：快速识别僵尸项目、高风险项目和核心资产项目。

### 2.2 作用
1.  **数字驾驶舱 (Digital Cockpit)**：作为 BI 工具（如 Grafana, Superset, PowerBI）的底层数据源，直接展示所有项目的红绿灯状态。
2.  **资源决策依据**：通过“工时偏差”和“活跃率”，帮助管理层决定是追加投入还是削减资源。
3.  **风险预警**：在项目发布前，强制检查“无Bug”、“覆盖率达标”、“流水线通过”等硬性指标。

### 2.3 意义
- **透明化**：让研发过程透明不可篡改。
- **标准化**：用统一的标尺（如活跃率计算公式）衡量所有团队。
- **闭环管理**：打通了从“计划(Milestone)”到“编码(Commit)”再到“质量(Sonar)”最后“交付(Release/Tag)”的全研发生命周期。

---

## 3. 指标体系详解 (Metrics Dictionary)

本视图包含 10 大维度，共计 40+ 个关键指标。以下是详细的业务含义与计算逻辑说明。

### 3.1 身份与元数据 (Identity & Meta)
| 字段名 | 业务含义 | 数据来源 |
| :--- | :--- | :--- |
| `group_name` | 所属产品线/业务组名称 | GitLab Groups |
| `project_name` | 项目名称 | GitLab Projects |
| `web_url` | 项目跳转链接 | GitLab Projects |
| `default_branch` | 默认分支 (通常为 main 或 master) | GitLab Projects |

### 3.2 资产属性 (Asset Profile)
| 字段名 | 业务含义 | 说明 |
| :--- | :--- | :--- |
| `visibility` | 可见性 (Public/Internal/Private) | 识别核心机密 vs 公共组件 |
| `archived` | 是否归档 | **重要**：已归档项目不应计入活跃统计，但属于历史资产 |
| `storage_mb` | 仓库体积 (MB) | 监控仓库是否膨胀（如误传大文件），计算逻辑：Bytes / 1024² |
| `star_count` | 关注度 (Star) | 衡量项目在组织内的受欢迎程度 |
| `forks_count` | 复用度 (Fork) | 衡量项目作为模板或基础组件的被复用次数 |

### 3.3 生命周期 (Lifecycle)
| 字段名 | 业务含义 | 计算逻辑 |
| :--- | :--- | :--- |
| `creation_date` | 建立日期 | 项目初始创建时间 |
| `age_days` | 项目 Age (天) | `Now - CreationDate`，衡量项目资历 |
| `last_release_date`| 最近发版日 | 项目最近一次打 Tag 的时间，**衡量交付活跃度** |
| `last_version` | 最新版本号 | 最近一次 Tag 的名称 (如 v1.2.0) |

### 3.4 计划与里程碑 (Plans & Milestones) `PM核心`
| 字段名 | 业务含义 | 说明 |
| :--- | :--- | :--- |
| `active_milestone` | 当前里程碑 | 当前正在进行的、状态为 Active 的最近一个里程碑标题 |
| `milestone_due_date`| 里程碑截止日 | 当前里程碑的预期结束时间，用于判断是否延期 |

### 3.5 成本与进度 (Cost & Progress) `PMO核心`
| 字段名 | 业务含义 | 计算逻辑 |
| :--- | :--- | :--- |
| `total_issues` | 需求总规模 | 项目累计 Issue 总数 |
| `issue_completion_pct`| 需求完成率 | `Closed Issues / Total Issues * 100%`，反映整体进度 |
| `estimated_hours` | 预估工时 (h) | 累加所有 Issue 的 `/estimate` 时间 |
| `spent_hours` | 实际投入工时 (h) | 累加所有 Issue 的 `/spend` 时间 |
| **`time_variance_hours`** | **工时偏差** | `Spent - Estimate`。**正数=超支，负数=节约**。用于成本审计 |

### 3.6 研发吞吐量 (Throughput)
| 字段名 | 业务含义 | 说明 |
| :--- | :--- | :--- |
| `total_mrs` | 累计 MR 数 | 项目历史总合并请求数 |
| `open_mrs_backlog`| 积压 MR 数 | 当前 Open 状态的 MR，**反映代码评审(Review)的瓶颈** |
| `merged_mrs` | 已合并 MR 数 | 实际合入主干的代码量，反映有效产出 |

### 3.7 质量与风险 (Quality & Risk) `QA核心`
| 字段名 | 业务含义 | 数据来源/说明 |
| :--- | :--- | :--- |
| `quality_gate` | 质量门禁状态 | SonarQube (OK/WARN/ERROR)。**ERROR 应禁止发布** |
| `bugs` | 代码 Bug 数 | SonarQube 扫描出的可靠性问题 |
| `vulnerabilities` | 安全漏洞数 | SonarQube 扫描出的安全性问题 |
| `coverage_pct` | 单元测试覆盖率 | 代码被测试用例覆盖的比例 |
| `build_status` | 构建状态 | GitLab 最近一次 Pipeline 状态 (Success/Failed) |

### 3.8 构建效能 (Build Efficiency) `Jenkins核心`
| 字段名 | 业务含义 | 数据来源/说明 |
| :--- | :--- | :--- |
| `jenkins_job_url` | 关联 Jenkins 任务 | Jenkins API |
| `last_build_result` | 最新构建结果 | Jenkins Build Result (SUCCESS/FAILURE/ABORTED) |
| `avg_build_duration`| 平均构建耗时 | 统计最近 100 次构建的平均时间 (秒) |
| `build_success_rate`| 构建成功率 (%) | `Success / Total Builds * 100%`，衡量代码集成稳定性 |
| `last_build_time` | 最后构建时间 | 最近一次构建完成的时间戳 |

### 3.9 工程产出 (Engineering Output)
| 字段名 | 业务含义 | 计算公式 (由用户定义) |
| :--- | :--- | :--- |
| `active_days` | 活跃天数 | 有代码提交的去重日期总数 |
| **`active_rate_pct`** | **活跃率** | `active_days / age_days * 100%`。衡量项目是“持续迭代”还是“僵尸化” |
| `total_commits` | 总提交数 | 累计 Commit 次数 |
| `avg_daily_commits` | 活跃天平均提交 | `total_commits / active_days`，衡量开发密集度 |
| `avg_author_commits`| 人均提交数 | `total_commits / author_count`，衡量团队平均贡献 |

### 3.9 代码规模 (Code Stats)
| 字段名 | 业务含义 | 说明 |
| :--- | :--- | :--- |
| `file_count` | 文件总数 | 包含代码源文件、脚本、配置等所有被扫描文件 |
| `code_lines` | 有效代码行 (NCLOC) | 去除注释和空行后的纯代码行数 |
| `comment_lines` | 注释行数 | 估算值，用于衡量代码可读性 |
| `comment_pct` | 注释率 | `Comments / (Code + Comments)` |

### 3.10 团队 (Team)
| 字段名 | 业务含义 | 格式示例 |
| :--- | :--- | :--- |
| `last_committer` | 最后责任人 | 最近一次修改代码的人员姓名 |
| `contributors` | 贡献者名单 | `姓名(提交数)` 格式，按贡献度降序排列。如：`张三(50), 李四(12)` |

---

## 4. 数据视图位置
- **SQL 视图名称**: `view_project_overview`
- **SQL 文件路径**: `devops_collector/sql/PROJECT_OVERVIEW.sql`
- **数据更新频率**: 取决于采集器 (Worker) 的同步周期 (建议每日同步)。

## 5. 总结
这份文档不仅是一个数据字典，更是一份**研发管理指南**。
- **对于 PM**: 盯紧 `issue_completion_pct` (进度) 和 `milestone_due_date` (死线)。
- **对于 Tech Lead**: 盯紧 `quality_gate` (质量) 和 `open_mrs_backlog` (评审阻塞)。
- **对于 PMO**: 盯紧 `time_variance_hours` (成本控制) 和 `active_rate_pct` (资源盘点)。

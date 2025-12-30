# DevOps 效能平台需求规格说明书 (SRS)

**项目名称**: DevOps Data Collector & Analytics Platform
**版本**: 3.7.0 (AI QA & Pydantic V2)
**日期**: 2025-12-20
**密级**: 内部公开

---

## 1. 引言 (Introduction)

### 1.1 编写目的
本文档旨在明确 **DevOps 效能平台** 的功能需求、非功能需求及接口规范，为开发团队、测试团队及项目干系人提供统一的执行标准。

### 1.2 背景
当前研发管理面临数据分散（GitLab/SonarQube/Jenkins/Jira 割裂）、指标主观（缺乏 DORA 等量化标准）、协作黑盒（无法感知真实工作量与瓶颈）等痛点。本系统通过构建统一的数据底座，实现研发过程的数字化、透明化与智能化。

### 1.3 适用范围
本系统适用于研发中心所有产研团队，覆盖需求、开发、测试、部署、运营全生命周期。

---

## 2. 总体描述 (Overall Description)

### 2.1 产品愿景
打造企业级研发效能“驾驶舱”，通过数据驱动研发效能提升，实现：
*   **可度量**: 全面落地 DORA、SPACE、Scrum 及 **Flow Efficiency** 指标体系。
*   **可溯源**: 打通“需求-代码-质量-部署”全链路。
*   **可审计**: 实现研发投入 (FinOps) 与业务产出 (Contracts) 的量化对齐，支持 R&D 资本化审计。

### 2.2 用户角色
| 角色 | 职责 | 核心诉求 |
| :--- | :--- | :--- |
| **研发工程师** | 代码开发、CR、修复 Bug | 查看个人产出、代码热力图、技术债预警 |
| **Tech Lead** | 团队管理、技术决策 | 监控项目进度、评审质量、识别架构腐烂、人才培养 |
| **PMO/管理层** | 效能度量、资源协调 | 查看部门记分卡、战略组合矩阵、投入产出比 (ROI) |
| **系统管理员** | 运维配置、权限管理 | 数据源配置、任务调度监控、日志审计 |

### 2.3 系统架构
系统采用 **微内核 + 插件化 (Micro-kernel & Plugins)** 架构：
*   **Core**: 负责配置管理、数据库连接、任务调度 (RabbitMQ)、身份归一化。
    *   `gitlab`: 采集 Commit, MR, Pipeline, Issue, Note。
    *   `sonarqube`: 采集 Coverage, Duplications, TechDebt。
    *   `jenkins`: 采集 Job metadata, Build history, Duration, Result (New)。
*   **Factory Registry (New)**: 引入 `PluginRegistry` 工厂，支持 Client 和 Worker 的零硬编码实例化，极大提升了新插件的接入效率。
*   **Modular Processing**: GitLab 同步逻辑解耦为 `DiffAnalyzer` (代码分析)、`IdentityMatcher` (身份识别) 和 `UserResolver` (组织映射) 三大独立模块。
*   **Data Warehouse**: PostgreSQL 星型模型存储，提供 SQL Views 层作为数据服务接口。

---

## 3. 功能需求 (Functional Requirements)

### 3.1 数据采集与同步 (R-COLLECT)

#### R-COLLECT-01: 多源数据适配
*   **描述**: 系统须支持 GitLab (v13+)、SonarQube (v8+) 和 Jenkins (v2.x+) 的 API 对接。
*   **验收标准**: 配置 URL/Token 后，能正确连通并获取 Version 信息。
#### R-COLLECT-02: Jira 深度数据
*   **描述**: 采集标签、修复版本、预估/实际工时、以及 Issue 链接（Dependency）。
*   **验收标准**: `jira_issues` 和 `traceability_links` 表能体现完整的链路关系。

#### R-COLLECT-03: 智能断点续传
*   **描述**: 针对大仓库（10万+ Commits），支持分批次 (Batch) 拉取。
*   **验收标准**: 中途中断同步（模拟 Kill 进程），重启后能从上次中断的页码/时间点继续，不重跑已同步数据。

#### R-COLLECT-04: 深度代码分析
*   **描述**: 采集代码变更明细，需区分“有效代码”、“空行”、“注释行”。
*   **验收标准**: `commit_file_stats` 表能准确记录每次提交的文件级增量；且支持通过配置文件忽略特定后缀文件（如 .lock, .min.js）。

#### R-PROCESS-03: 深度数据回放 (Data Replay)
*   **描述**: 支持基于 Staging 层的原始数据进行逻辑重算（无需再次请求 API）。
*   **验收标准**: 运行 `reprocess_staging_data.py` 后，能无损更新业务表数据，且支持指定 Schema Version 进行差异化解析。

### 3.2 数据治理与处理 (R-PROCESS)

#### R-PROCESS-01: 统一身份归一化
*   **描述**: 将不同工具（GitLab账号、Sonar账号、Email别名）关联到唯一的自然人 (`users`)。
*   **验收标准**: 同一用户使用不同邮箱提交的代码，在个人产出统计中应合并计算。支持标记“虚拟账号”以处理外包/离职人员。

#### R-PROCESS-02: 组织架构映射
*   **描述**: 自动发现 GitLab Group 层级，映射为公司组织架构（Dept/Team）。
*   **验收标准**: 新增 Group 后，系统应自动创建对应的 `Organization` 节点，并正确归属项目。

#### R-PROCESS-03: 跨部门协作识别 (InnerSource)
*   **描述**: 识别跨部门的代码提交行为 (InnerSource)。
*   **验收标准**: 提供 `view_pmo_innovation_metrics`，能准确计算出“非本部门项目”的贡献比例。

### 3.3 效能洞察与分析 (R-ANALYTICS)

#### R-ANALYTICS-01: DORA 四大指标
*   **描述**: 计算部署频率、变更前置时间、变更失败率、MTTR。
*   **验收标准**: 提供 SQL View `view_pmo_dept_ranking`，数据误差 < 5%。

#### R-ANALYTICS-02: 团队健康度雷达
*   **描述**: 识别过度加班 (WLB) 和 冲刺后遗症。
*   **验收标准**: 能通过 `view_hr_retention_risk` 输出周末/深夜提交占比 > 30% 的高危人员名单。

#### R-ANALYTICS-03: 代码评审质量分析
*   **描述**: 识别“橡皮图章”评审（0交互）与“过度纠结”（>5轮交互）。
*   **验收标准**: 能正确区分 Review 互动的深度 (Comments Count)。

#### R-ANALYTICS-04: 架构演进分析
*   **描述**: 识别逻辑耦合（Co-change）与单点依赖（Bus Factor）。
*   **验收标准**: 识别代码库中的高频修改热点文件。

#### R-ANALYTICS-05: 战略投资组合分析 (Strategic Portfolio)
*   **描述**: 基于 **DevOps 波士顿矩阵** 模型，综合开发速度与代码质量，自动将项目划分为明星、现金牛、瘦狗、问题儿童四类。
*   **验收标准**: 提供 `view_pmo_portfolio_matrix`，能正确计算 X/Y 轴坐标及象限归属。

#### R-ANALYTICS-06: 风险与合规治理 (Governance & Risk)
*   **描述**: 监控研发流程红线（如绕过 CR 直接发布）及安全底线（高危漏洞积压）。
*   **验收标准**: 提供 `view_pmo_governance_risk`，支持按部门统计违规率和安全债务。

#### R-ANALYTICS-07: 投入产出效能 (ROI Efficiency)
*   **描述**: 量化研发投入（FTE/工时）与产出（MR/Issue）的比率，回答“钱花得值不值”。
*   **验收标准**: 提供 `view_pmo_roi_efficiency`，计算 Throughput per FTE 和 Cost per Issue。

#### R-ANALYTICS-08: 人才能力画像 (HR Capability)
*   **描述**: 多维评估工程师能力（编码/质量/协作），识别技术专家与高潜人才。
*   **验收标准**: 提供 `view_hr_user_capability_profile` 及 `view_hr_user_tech_stack`。

#### R-ANALYTICS-09: 构建效能分析 (Jenkins Analytics) (New)
*   **描述**: 追踪构建成功率、构建耗时趋势、构建触发分布（SCM vs Manual）。
*   **验收标准**: 提供 SQL View，能准确输出各 Job 的平均耗时及构建健康度。

#### R-ANALYTICS-10: 战略对齐与 OKR (OKR & Alignment) (New)
*   **描述**: 支持录入 OKR 目标并将其与产品、项目的产出指标自动化关联。
*   **验收标准**: 能展示 OKR 进度的实时自动化更新。

#### R-ANALYTICS-11: 财务与 ROI 分析 (FinOps & ROI) (New)
*   **描述**: 采集基础设施与人力成本，计算单一需求或产品的 ROI。
*   **验收标准**: 提供 `view_pmo_roi_efficiency`，展示单位投入的产出效率 (Throughput per Dollar)。

#### R-ANALYTICS-12: 流动效能分析 (Flow Efficiency) (New)
*   **描述**: 追踪任务在各状态的停留时间，识别“忙碌的等待”。
*   **验收标准**: 自动提取 'blocked' 标签时间，计算 Flow Efficiency = (Cycle Time - Wait Time) / Cycle Time。

#### R-ANALYTICS-13: AI 智能归因与测试生成 (AI QA) (New)
*   **描述**: 利用 LLM 对非结构化 Commit Message 和 Issue Description 进行语义分析，并驱动 **AI 自动化测试用例生成 (AC-to-Steps)**。
*   **验收标准**: 自动填充 `ai_category` 准确率 > 80%；自动生成的测试步骤应覆盖 100% 的验收标准 (Acceptance Criteria)。
#### R-NOTIFY-01: 多渠道风险告警
*   **描述**: 支持基于异常指标（进度落后、质量红线、跨项目阻塞）的自动推送。
*   **验收标准**: 支持企业微信、飞书、钉钉三方渠道，延迟 < 5min。

#### R-NOTIFY-02: 实时业务通知 (SSE) (New)
*   **描述**: 建立 Server-Sent Events 通道，实现“测试完成”、“评审通过”、“流水线失败”等高频事件的毫秒级推送。
*   **验收标准**: 前端 Dashboard 无需刷新即可接收通知；连接中断具备自动重连机制。

### 3.4 系统安全与交互 (R-SEC-OPS)

#### R-AUTH-01: 独立认证体系
*   **描述**: 构建基于 OAuth2 + JWT/Bearer Token 的认证中心，解耦对单一 IM 工具的依赖。
*   **验收标准**: 支持用户注册、登录、Token 签发与自动续期；所有 API 均需校验 Token 有效性。

#### R-APPS-01: 服务台交互门户 (Service Desk)
*   **描述**: 提供面向业务人员的轻量级 H5 门户，支持 Bug 提报、需求提交及进度查询。
*   **验收标准**: 自动读取登录态 (Token) 填充提单人信息，无需手工输入；支持查看“我提交的”工单状态。

---

## 4. 非功能需求 (Non-Functional Requirements)

### 4.1 性能要求
*   **吞吐量**: 单 Worker 进程处理 Commit 速度不低于 50/s。
*   **内存控制**: 采用 Generator 流式处理，处理 1GB+ 仓库时内存占用不超过 500MB。
*   **幂等性**: 所有写操作须支持幂等，重复运行不会导致数据重复。

### 4.2 可靠性
*   **容错**: API 请求失败（如 Network Error）须具备指数退避重试机制 (Exponential Backoff)。
*   **隔离**: 单个项目的采集失败不应阻塞其他项目的执行。

### 4.3 可扩展性
*   **插件化**: 新增数据源（如 Jira）时，不应修改 Core 层代码，仅需在 `plugins/` 目录下新增对应包。
*   **Schema 演进**: 必须支持 API 字段变更，通过 `SCHEMA_VERSION` 机制保证向后兼容性。

### 4.4 安全性
*   **凭证管理**: 所有 Token 严禁明文硬编码，必须通过 `config.ini` 或环境变量注入。
*   **数据脱敏**: 日志中严禁打印 Token、密码等敏感信息。

---

## 5. 接口需求 (Interface Requirements)

### 5.1 数据库接口
*   系统对外暴露一系列 **SQL Views** (位于 `devops_collector/sql/`) 作为标准数据接口，供 BI 工具（Superset/Grafana）直接连接查询。
*   包含：`PROJECT_OVERVIEW.sql`, `PMO_ANALYTICS.sql`, `HR_ANALYTICS.sql` 等。

### 5.2 消息队列接口
*   采用 **RabbitMQ** 作为任务总线。
*   Exchange: `devops.direct`
*   Queue: `gitlab_tasks`
*   Payload Format: JSON (`{"source": "gitlab", "project_id": 101, "job_type": "incremental"}`)

---

## 6. 附录 (Appendix)

### 6.1 术语表
*   **DORA**: DevOps Research and Assessment，业界通用的效能评估标准。
*   **SPACE**: 开发者生产力框架 (Satisfaction, Performance, Activity, Communication, Efficiency)。
*   **WLB**: Work-Life Balance，工作生活平衡指数。
*   **Bus Factor**: 巴士系数/卡车系数，指有多少关键人员被巴士撞了项目就会瘫痪，衡量单点风险。

### 6.2 参考文献
*   《DevOps Data Collector 系统架构设计文档 (ARCHITECTURE.md)》
*   《DevOps Data Dictionary (DATA_DICTIONARY.md)》
*   《PMO Analytics Plan (PMO_ANALYTICS_PLAN.md)》

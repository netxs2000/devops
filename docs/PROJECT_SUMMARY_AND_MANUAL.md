# DevOps Data Collector - 项目总结与系统功能手册

**版本**: 4.1.0
**日期**: 2026-01-08
**维护**: DevOps 效能平台团队

---

## 📚 1. 项目综述 (Project Overview)

### 1.1 背景与目标

在现代软件研发过程中，研发数据分散在不同的工具链中（如 GitLab 管理代码与过程，SonarQube 管理质量），形成了数据孤岛。**DevOps Data Collector** 旨在解决这一痛点，通过构建统一的数据采集与分析平台，将分散的研发数据聚合为企业级资产。

### 1.2 核心价值

1. **打通数据孤岛**: 统一 GitLab、SonarQube 和 Jenkins 数据，实现开发、质量与构建的关联分析。
2. **统一身份认证**: 解决工具间账号不一致问题，通过邮箱自动聚合“自然人”在不同系统的活动。
3. **效能度量标准化**: 自动化计算 DORA 指标（部署频率、变更前置时间等），为研发效能改进提供数据支撑。
4. **战略与风险洞察**: 通过波士顿矩阵和风险看板，提供从 CTO 到 PMO 的战略决策支持。

---

## 🛠️ 2. 系统功能手册 (System Function Manual)

### 2.1 多源数据采集 (Multi-Source Collection)

系统采用 **Airbyte** 作为核心数据同步引擎，结合**插件化架构**，支持多种数据源的扩展。目前 **GitLab**, **SonarQube**, **Jira**, **Jenkins** 等核心插件均已通过 Airbyte Connector 完成集成，实现了标准化的 ELT 数据接入。

#### 2.1.1 GitLab 采集插件

* **元数据同步**: 自动同步项目名称、描述、Star 数、Fork 数等。
* **代码提交 (Commits)**:
  * 采集 Commit 基础信息（作者、时间、Message）。
  * **深度 Diff 分析**: 使用 `DiffAnalyzer` 自动拆解代码变更，区分**有效代码行**、**注释行**和**空行**，通过 `commit_file_stats` 表记录文件级明细。
* **合并请求 (Merge Requests)**: 记录 MR 状态、评审人、合并时间，用于计算 CR 耗时。
* **流水线与部署 (CI/CD)**:
  * 采集 Pipeline 状态与时长。
  * 采集 Deployment 记录（环境、Ref），作为 **DORA 指标**的核心数据源。
* **过程数据**: 采集 Issue（需求/缺陷）和 Notes（评论），支持沟通密度分析。
* **CALMS 深度扫描 (New)**: 自动采集 Issue 的 **State/Label/Milestone Resource Events**。通过追踪这些原子事件，系统能够量化“等待浪费”、“需求跳变频率”以及“跨团队响应速度”，为组织文化扫描提供核心依据。
* **工程卓越度增强**: 自动计算 MR 的**评审轮次 (Review Cycles)**、**有效评论数**、**代码规范状态 (Lint)** 以及**非工作时间提交频率 (Work-Life Balance)**。
* **敏捷流动效能 (Agile Flow)**: 追踪 Issue 的 `state_transitions`，自动计算 **Cycle Time**。识别 `blocked` 标签时段，量化**阻塞时长**与**流动速率 (Flow Efficiency)**。
* **AI 价值识别**: 利用 LLM 自动对 Commit 和 Issue 进行分类 (Feature/Maintenance/Internal) 并生成业务价值摘要 (AI Summary)。
* **制品与依赖扫描**: 同步 GitLab Package Registry 中的制品元数据，并自动建立跨项目的模块依赖图谱。
* **共享文化 (Sharing)**: 采集 Wiki 变更频率，作为知识库活跃度（Sharing 维度）的度量。
* **原始数据暂存 (Staging)**: 所有采集到的 JSON 数据（Issue, MR, Pipeline, Deployment）均带有 Schema Version 落盘至 `raw_data_staging` 表，支持数据回溯。

#### 2.1.2 SonarQube 采集插件

* **自动映射**: 基于项目路径规则自动关联 GitLab 项目与 SonarQube 项目。
* **质量快照**: 周期性拉取代码覆盖率 (Coverage)、技术债务 (Tech Debt)、Bug 数等指标，存入 `sonar_measures`。
* **趋势记录**: 记录质量随时间的变化趋势，支持历史回溯。
* **Issue 同步 (可选)**: 支持同步具体的代码异味、Bug 和漏洞详情（默认关闭，可通过配置开启）。

#### 2.1.3 Jenkins 采集插件

* **任务发现 (Job Discovery)**: 自动同步 Jenkins 实例中的所有 Job 列表及其元数据。
* **构建历史 (Builds)**:
  * 采集构建状态 (Result)、耗时 (Duration)、时间戳。
  * **触发源分析**: 识别构建是由 SCM 变更、用户手动、还是定时任务触发。
* **跨系统映射**: 自动通过 Job 名称匹配 GitLab 项目路径，建立构建与代码库的血缘关系。
* **增量同步**: 自动记录同步断点，仅拉取最新的构建记录，支持大规模任务同步。

#### 2.1.4 Jira 采集插件 (New)

* **敏捷实体同步**: 完整拉取项目 (Project)、看板 (Board)、迭代 (Sprint) 和问题 (Issue)。
* **变更历史 (Changelog)**: 记录状态流转过程（如 To Do -> In Progress），支持计算周期时间 (Cycle Time)。
* **工作负载分析**: 统计 Assignee 分布，支持 HR 维度的资源投入分析。

#### 2.1.5 禅道 (ZenTao) 采集插件

* **全量生命周期**: 采集产品 (Product)、计划 (Plan)、需求 (Story) 和执行 (ExecutionInstance)。
* **结构化映射**: 将禅道内部复杂的层级关系映射为统一的 Issue 模型，确保跨源数据统计的一致性。

#### 2.1.6 Nexus 采集插件 (New)

* **资产普查**: 自动同步 Nexus 仓库中的组件 (Components) 与资产 (Assets)。
* **校验和记录**: 采集 SHA1/SHA256 校验和，为软件包的唯一性验证提供支持。

#### 2.1.7 JFrog Artifactory 采集插件 (New)

* **制品追溯**: 基于 AQL (Artifactory Query Language) 采集制品元数据。
* **质量与安全**: 同步下载量统计 (Stats) 和 Xray 安全扫描摘要 (Vulnerabilities)。
* **构建血缘**: 自动提取制品属性中的 `build.name`，实现从制品回溯到构建任务的完整链路。

#### 2.1.8 财务系统集成 (FinOps Integration) 🌟 (New)

* **成本科目 (CBS)**: 建立财务级的成本拆解树，支持 Labor、Infrastructure 分类。
* **采购合同**: 记录支出合同（如云服务器订阅），支持线性摊销成本流水生产。
* **收入合同与收款**: 支持 3-4-3 等多种回款计划。
* **技术-财务对齐**: 将合同收款节点与 GitLab Milestone 挂钩。里程碑关闭即视为回款条件达成（或风险预警）。

#### 2.1.9 统一测试管理 (GTM - Generic Test Management) 🚀 (New)

针对 GitLab 社区版 (CE) 缺乏原生测试用例管理的痛点，系统提供了一个基于 **GTM** 前缀隔离的嵌入式测试管理解决方案。采用 `GTM` 前缀（如 `GTMTestCase`, `GTMRequirement`）是为了确保模型逻辑与自动化测试框架（如 pytest）的自动收集机制完全隔离，避免命名冲突。

* **测试用例库 (Test Case Repository)**:
  * **结构化录入**: 支持标题、优先级、测试类型、预置条件、以及动态增减的结构化测试步骤。
  * **议题驱动存储**: 用例以 Markdown 模板形式存储在 GitLab Issues 中，利用 `type::test` 标签进行自动识别，无需维护第三方数据库即可实现数据持久化。
* **执行与反馈 (Execution Feedback)**:
  * **状态追踪**: 支持 Passed, Failed, Blocked 状态一键切换，并自动同步 GitLab 标签。
  * **自动化审计线索 (Audit Trail)**: 每次执行不仅更新标签，还会自动在 Issue 下发表评论（Comment），记录执行人、结果、关联的流水线 ID 及时间戳。
* **缺陷生命周期管理 (Defects Kanban)**:
  * **一键报障**: 失败用例支持快捷生成 GitLab Bug Issue 链接，自动预填测试上下文（步骤、预期结果）。
  * **缺陷看板**: 提供专门的 Defects 视图，集中展示项目中所有 Bug 的修复状态、优先级、修复时长等指标，计算**缺陷修复率**。
* **CI/CD 与质量报告**:
  * **流水线实时联动**: 通过 Webhook 实时监听 GitLab Pipeline 事件，在测试执行时自动关联当前的构建任务 (Pipeline ID) 和部署环境。
  * **一键导出质量报告**: 自动生成 Markdown 格式的《项目质量报告》，包含质量仪表盘（通过率等）、缺陷全景图、详细执行记录。
* **地域质量分析与 AI 证言 (Province Analytics & AI Testimony) 🚀 (New)**:
  * **地域热力扫描**: 自动识别 Issue 中的 `province::*` 标签，构建极坐标热力图 (Polar Area Chart)，直观定位各省份的缺陷积压与分布情况。
  * **智能质量证言**: 系统基于需求覆盖率、通过率及地域分布数据，自动生成结构化的《版本质量证言》，点名高风险地域并给出专业 QA 准入建议。

#### 2.1.10 服务台与认证 (Service Desk & Auth) 🌟 (New)

* **独立认证**: 不再依赖第三方 IM 验证，内置基于 OAuth2 的用户注册/登录模块，支持 Token 自动续期。
* **极简提单**: 提单页面 (`frontend/service_desk_*.html`) 自动透传登录态，业务人员无需重复输入姓名、部门等基础信息。
* **实时交互**: 引入 **Server-Sent Events (SSE)**，将测试执行结果、需求评审意见、流水线失败告警等高频事件，以毫秒级延迟推送到用户浏览器。

### 2.2 智能数据处理 (Intelligent Processing)

#### 2.2.1 统一身份归一化 (Identity Matcher)

* **独立模块化**: 已重构为独立模块 `IdentityMatcher` 和 `UserResolver`，支持跨插件调用。
* **自动匹配**: 系统内置智能匹配引擎，优先基于 **Email** 将 Git 提交记录关联到全局 `users` 表。
* **模糊匹配**: 支持基于 Name 或 Username 前缀的辅助匹配策略。
* **虚拟账号管理**: 自动标记无公司邮箱的外部贡献者，支持后续手工归并。

#### 2.2.2 插件工厂与实例化 (Plugin Factory) (New)

* **零耦合分发**: 主 Worker 进程通过 `PluginRegistry` 动态创建 Client 和 Worker 实例，彻底消除 `if-elif` 硬编码。
* **统一配置路由**: 任务根据 `source` 类型自动关联 `Settings` 对象中的对应配置项。

#### 2.2.3 断点续传与增量同步 (Resumable Sync)

* **状态机**: 每个项目维护 `content_status` (PENDING/SYNCING/COMPLETED)。
* **从断点恢复**: 记录同步进度（如 Page Number 或 Last Synced Time），中断后重新运行通过 `sync_state` 自动接续，无需从头重跑。
* **Generator 流式处理**: 客户端采用 `yield` 模式逐页拉取数据，结合 `batch save` 自定义批处理，有效防止大规模项目同步时的内存溢出 (OOM)。

* **层级构建**: 将 Group/Subgroup 映射为标准的四级组织架构，支持部门层级的效能聚合查询。

#### 2.2.4 跨系统映射逻辑 (Cross-System Mapping) (New)

系统通过“约定优于配置”的原则打通不同工具链的数据：

* **SonarQube -> GitLab**: 默认基于 SonarQube 的 `Project Key` 或 `Project Name` 匹配 GitLab 的 `path_with_namespace`。
* **Jenkins -> GitLab**: 基于 Jenkins Job 的 `fullName` 或 `name` 与 GitLab 项目名称进行模糊及完全匹配。
* **Jira -> GitLab**: 通过关联配置或项目 Key 的命名规范实现双向追踪。
* **制品库 -> 构建/代码**:
  * **JFrog**: 通过 `build.name` 属性自动关联至对应的 `jenkins_jobs`。
  * **Nexus**: 基于 Maven GAV (GroupId, ArtifactId) 坐标与 GitLab 项目路径的命名契约进行关联。
* **核心关联健**: 统一指向 `projects.id`，实现“一个项目，全链洞察”。

#### 2.2.5 容错与自动重试 (Fault Tolerance & Retry) (New)

系统内置了工业级的异常处理与重试机制，确保在复杂网络环境下的高可用性：

* **智能重试策略**: 基于 `tenacity` 实现指数退避重试（Exponential Backoff）。
* **精细化异常分类**:
  * **可重试异常**: 如网络超时、连接断开、5xx 服务端错误、429 速率限制。
  * **非重试异常**: 如 401/403 认证错误，系统将立即停止并记录 ERROR 日志，防止无效重试。
* **速率限制适配**: 自动解析 API 返回的 `Retry-After` 头部，动态调整等待时间。

#### 2.2.6 原始数据回放 (Data Replay) (New)

* **Schema Evolution**: 支持 `SCHEMA_VERSION` 常量管理（如 GitLab v1.1），应对 API 字段变更。
* **Reprocessing**: 提供 `reprocess_staging_data.py` 脚本，可直接从 Staging 表读取历史 JSON 数据并重新运行业务解析逻辑，无需再次请求外部 API。这对于**修复历史数据逻辑错误**或**新增字段回填**至关重要。

#### 2.2.8 AI 辅助归因服务 (AI Enrichment Service) 🌟 (New)

* **自动化分类**: 基于 LLM 对 Commit Message 和 Issue 内容进行语义识别。
* **置信度审计**: 记录 AI 分类置信度，支持人工抽检与自动化阈值过滤。

---

## 📊 3. 深度洞察与分析 (Advanced Analytics)

本系统内置了多维度分析体系，从**效能、质量、协作、价值、行为、架构、战略**七个维度全面量化研发过程。

### 3.1 研发效能 DORA 指标 (DORA Metrics)

* **核心逻辑**: 通过四个关键指标量化软件交付绩效，平衡“速度”与“稳定性”。

* **价值**: 对标业界标准 (DevOps Research and Assessment)，持续监控并优化研发交付链条的效率与质量。
* **维度**:
  * **部署频率 (Deployment Frequency)**: 成功部署到生产环境的频率。
  * **变更前置时间 (Lead Time for Changes)**: 代码从提交 (Commit) 到部署至生产环境 (Deploy) 的时长。
  * **变更失败率 (Change Failure Rate)**: 导致失败/回滚或需要热修复的部署占比。
  * **平均恢复时间 (Time to Restore Service)**: 发生生产故障后恢复服务所需的平均时间 (MTTR)。
* **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql` (Dept Ranking)

### 3.2 个人综合贡献度 (User Impact Score)

* **核心逻辑**: 摒弃单一的“代码行数”评价，构建涵盖代码产出、团队协作、问题解决的多维度加权评分模型。

* **价值**: 公平量化开发者产出，避免单一指标偏颇，引导高质量的工程行为。
* **维度**:
  * **代码产出**: `Commits Count`, `Lines Added` (净增)。
  * **协作贡献**: `Merge Requests Merged` (核心产出), `Merge Requests Opened`。
  * **问题管理**: `Issues Resolved` (解决), `Issues Reported` (发现)。
* **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.3 项目价值评估 (Project Value Index)

* **核心逻辑**: 结合活跃度、规模、稳定性、协作度构建多维度的项目价值指数。

* **价值**: 识别核心资产与僵尸项目，通过 `value_score` 进行量化分级，辅助资源投入决策。
* **维度**:
  * **活跃度 (Activity)**: `active_days`。
  * **规模 (Scale)**: `commit_count` + `storage_size`。
  * **稳定性 (Stability)**: `tags_count`。
* **实现方式**: `devops_collector/sql/PROJECT_OVERVIEW.sql`

### 3.4 部门级平衡记分卡 (Department Scorecard)

* **核心逻辑**: 从交付、活力、质量三个维度横向对比各中心/部门表现。

* **价值**: 识别部门间的能力差异，发现管理短板，推动组织效能对齐。
* **维度**:
  * **交付效能**: DORA 四项指标部门均值。
  * **组织活力**: 人均产出 (Commit/MR per Person), 活跃人力占比。
  * **资产质量**: 维护代码总量, Bug 密度。
* **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql`

### 3.5 战略对齐 (OKR & Alignment) (New)

* **核心逻辑**: 将底层研发交付指标 (API 调用量、构建频率等) 向上映射至业务目标 (Objective)。

* **价值**: 让技术产出变得“可理解”，量化技术对业务目标的实际贡献。
* **维度**: 目标进度百分比, KR 信心指数。

### 3.6 成本与 ROI (FinOps) (New)

* **核心逻辑**: 结合服务器/云成本与人力工时成本，计算产研投入产出比。

* **价值**: 优化资源配置，识别长尾低价值项目，支持 R&D 资本化审计。
* **维度**: 单位 Story 交付成本, 部门月度云资源开销趋势, **资本化率 (CAPEX%)**。

### 3.7 流动效能分析 (Flow Efficiency) 🌟 (New)

* **核心逻辑**: 追踪任务从创建到交付的全生命周期状态流转。

* **价值**: 识别流程中的“等待黑盒”，量化阻塞带来的损失。
* **维度**:
  * **周期时间 (Cycle Time)**: 从开发到完成。
  * **流动速率 (Flow Efficiency)**: `ActiveTime / TotalTime`。

### 3.7 开发者代码热力图 (User Heatmap)

* **核心逻辑**: 可视化展示开发者每日的提交频率 (Contribution Graph)。

* **价值**: 直观呈现开发者的工作节奏与活跃模式。
* **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.6 开发者全生命周期 (User Lifecycle)

* **核心逻辑**: 基于首次和最后一次提交时间，计算人员在职/活跃周期及留存状态。

* **价值**: 辅助 HR 和团队 Lead 分析人才留存率 (Retention) 和流失风险。
* **维度**:
  * **活跃跨度**: `active_days_count` (Last - First)。
  * **当前状态**: `status` (Active/Dormant/Churned)。
* **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.7 开发者技术广度 (Tech Stack Breadth)

* **核心逻辑**: 通过分析代码提交文件的后缀名，识别开发者掌握的编程语言种类与分布。

* **价值**: 识别团队中的 **全栈工程师** (Full Stack) 或跨语言技术专家。
* **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.8 代码评审影响力 (Code Review Impact)

* **核心逻辑**: 仅仅写代码是不够的，**评审他人代码**是高级工程师的重要职责。

* **价值**: 识别团队中的 **技术把关人** (Gatekeeper) 和乐于指导新人的 **导师** (Mentor)。
* **维度**:
  * **评审参与度**: `mrs_reviewed_count`。
  * **交互强度**: `avg_comments_per_review`。
* **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.9 版本发布分析 (Release Analytics)

* **核心逻辑**: 以 Tag 为里程碑，自动划定“版本区间”，统计每个版本包含的提交量和贡献者阵容。

* **价值**: 自动生成“Release Notes”的核心数据，回顾每个版本的开发体量。
* **实现方式**: `devops_collector/sql/PROJECT_OVERVIEW.sql`

### 3.10 代码构成分析 (Code Composition)

* **核心逻辑**: 通过重建代码历史，还原项目当前的文件构成。

* **价值**: 无需 Clone 代码库即可分析项目的技术栈分布 (Python vs Go)、文件规模分布等。
* **实现方式**: `devops_collector/sql/PROJECT_OVERVIEW.sql`

### 3.11 评审民主度与协作熵 (Review Democracy & Entropy) 🌟 (New)

* **核心逻辑**: 通过分析代码评审 (CR) 轨迹，识别“一言堂”或“无效沟通”风险。
  * **民主度**: 统计 MR 的独立评审人多样性。
  * **协作熵**: 统计单次变更伴随的平均人工评论数。
  * **乒乓指数**: 统计 MR 打回修订的轮次。

* **价值**: 提升代码质量把关实效，防止技术负债隐秘堆积。
* **实现方式**: `devops_collector/sql/TEAM_ANALYTICS.sql` (`view_team_review_quality_entropy`)

### 3.12 团队倦怠雷达 (Burnout Radar)

* **核心逻辑**: 利用时间戳数据感知团队健康度，寻找不可持续工作的信号。

* **价值**: 提前感知团队的过度劳累，预防人才流失。
* **维度**:
  * **WLB 指数**: 工作时间外及周末的提交占比。
  * **冲刺后遗症**: 密集提交期（如发版前）之后紧接着的 Bug 率。
* **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.13 隐性工作与流程偏离 (Process Deviation)

* **核心逻辑**: 捕捉未被正规管理流程 (Jira/Issue) 覆盖的工作，以及被遗忘的库存。

* **维度**:
  * **游离代码率**: 未关联 Issue 的提交占比。
  * **幽灵分支**: 沉睡超过 30 天且未合并的分支。

### 3.14 代码演进与架构熵 (Code Evolution)

* **核心逻辑**: 分析代码变更的性质（重构 vs 新增）及模块间的隐性依赖。

* **维度**:
  * **重构比率**: 删除线/新增线 趋近于 1。
  * **逻辑耦合热度**: Co-change Frequency (异构模块同时修改)。

### 3.15 跨边界协作力与内源生态 (InnerSource Impact)

* **核心逻辑**: 衡量组织内部的开源文化与知识共享情况。
  * **内源贡献率**: 跨部门 MR 贡献占比。
  * **组件复用率**: 内源组件被外部项目引用的广度。

* **价值**: 打破部门墙，通过技术复利降低重复造轮子成本。
* **计算逻辑**: `InnerSource Index = (跨部门提交的 MR 数 / 总 MR 数) * 0.4 + (被外部引用的组件数 / 总组件数) * 0.6`。
* **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql` (`view_pmo_innersource_reuse_heatmap`)

### 3.19 人员效能六边形 (Ability Hexagon Persona) 🌟 (New)

* **核心逻辑**: 从生产力、质量、协作、响应性、广度、持续性六个维度对员工进行全方位刻画。

* **价值**: 识别团队中的“扫地僧”（高质量低产量）与“冲锋队长”（高产量高响应）。
* **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql` (view_user_ability_hexagon)

### 3.20 风险预警推送 (Risk Notification) 🌟 (New)

* **核心逻辑**: 自动识别并推送 进度、质量、协作、安全 四大类红线告警。

* **价值**: 让风险发现从“被动报表”转为“主动触达”。
* **渠道**: 企业微信、飞书、钉钉推送。
* **配置**: 详见 `METRIC_THRESHOLDS_GUIDE.md` (指标预警阈值配置白皮书)。

### 3.22 隐性满意度 (Shadow Satisfaction Index) 🌟 (New)

* **核心逻辑**: 在无问卷调查的情况下，通过“行为指纹”推导交付体验。
  * **响应性 (Penalty)**: Bug 修复时长的 SLA 扣分。
  * **冲突性 (Penalty)**: 高争议需求评论密度的扣分。
  * **返工性 (Penalty)**: 需求重开记录的扣分。

* **价值**: 识别那些“交付了但业务体验极差”的风险项目。
* **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql` (`view_pmo_customer_satisfaction`)

### 3.21 自动化归责逻辑 (Automated Attribution) 🌟 (New)

* **核心逻辑**: 系统如何判定一个 Bug 或 Lint 问题属于谁？
  * **SCM Blame 归责**: 通过 SonarQube 的 Git Blame 插件实时定位代码行的最后修改人。
  * **提交关联归责**: 所有的 Lint 遵循度和 CI 失败记录均与该 Commit 的 Author 绑定。
  * **缺陷引入者追溯**: 通过 `traceability_links` 建立 MR 与业务 Bug 的逻辑关联，实现从结果到原因的“穿透式归属”。

* **价值**: 确保“能力六边形”中质量维度的客观公正。

### 3.23 架构脆性指数 (Architectural Brittleness Index) 🌟 (New)

* **核心逻辑**: 识别研发资产中因“高耦合+高变动+低质量”构成的技术黑洞。
  * **依赖权重**: 外部引用的入度因子。
  * **动荡权重**: 过去 90 天代码流转频率。
  * **硬伤权重**: 圈复杂度与单测覆盖率得分。

* **价值**: 预防系统性技术塌陷，精准指导重构资源投入。
* **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql` (`view_pmo_architectural_brittleness`)

### 3.24 计划确定性指数 (Planning Certainty Index) 🌟 (New)

* **核心逻辑**: 量化团队的承诺履行能力与估算水准。
  * **估算准确度**: 统计实耗工时与预估工时的偏差。
  * **交付稳定性**: 监控截止日期的延期频次。

* **价值**: 辅助 PMO 识别“靠谱团队”，提升业务排期的可预见性。
* **实现方式**: `devops_collector/sql/TRADITIONAL_PM_ANALYTICS.sql` (`view_pmo_planning_certainty`)

### 3.25 “胶水人”贡献模型 (The Glue-Person Index) 🌟 (New)

* **核心逻辑**: 识别通过非代码产出维持团队高效运作的“灵魂人物”。
  * **知识布道**: 活跃在 Wiki 和技术文档建设的一线。
  * **流程守护**: 主动修正 Issue 状态、标签，确保研发流程合规。
  * **协作催化**: 在评论区积极响应、解决争议、解除他人阻塞。

* **价值**: 完善人才评价体系，奖励那些让别人更高效的开发者。
* **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql` (`view_hr_glue_person_index`)

### 3.26 软件供应链流转效率 (Software Supply Chain Velocity) 🌟 (New)

* **核心逻辑**: 监控制品从代码合并到生产发布的全生命周期。
  * **构建转换率**: 统计维持一次稳定发布所需的平均构建次数。
  * **环境停留时延**: 量化制品在 Staging/UAT 环境待部署的时长。
  * **交付漏斗**: 关联 Pipeline 成功率与 Deployment 频次。

* **价值**: 识别交付流程中的“物理淤积点”，推动持续交付 (CD) 的深度落地。
* **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql` (`view_pmo_software_supply_chain_velocity`)

### 3.27 组织依赖透明度 (Organization Dependency Transparency) 🌟 (New)

* **核心逻辑**: 识别跨部门的协作阻塞节点与链式延期风险。
  * **脆弱性指数**: 统计受外部部门阻塞的任务占比。
  * **影响拓扑**: 识别“关键路径”上的跨部门依赖。

* **价值**: 为组织治理提供依据，识别那些被“上游”拖累的项目。
* **实现方式**: `devops_collector/sql/TRADITIONAL_PM_ANALYTICS.sql` (`view_pmo_org_dependency_transparency`)

### 3.16 战略投资组合 (Strategic Portfolio) (New)

* **核心逻辑**: 基于波士顿矩阵，将项目划分为 Stars (高质高产), Cash Cows (高质低产), Dogs (低质低产), Problem Children (低质高产)。

* **价值**: 辅助 CTO 进行研发资源分配决策。
* **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql`

### 3.17 风险与合规治理 (Governance & Risk) (New)

* **核心逻辑**: 监控 Direct Push (绕过流程) 和 Security Blockers (安全债务)。

* **价值**: 确保研发流程合规，降低生产风险。
* **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql`

### 3.18 投入产出效能 (ROI Efficiency) (New)

* **核心逻辑**: 计算研发投入 (FTE, Hours) 与产出 (Throughput) 的转化率。

* **价值**: 回答 "钱花得值不值"。
* **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql`

---

## 💰 4. 财务视角的研发效能洞察 (Finance Analytics)

### 4.1 项目真实盈利能力分析 (Project Profitability) 🌟 (New)

* **核心逻辑**: 量化项目的收入、成本与毛利率。
  * **收入端**: 汇总已达成的合同回款节点。
  * **成本端**: 人力成本 + 云成本 + 外包成本。

* **价值**: 识别"伪需求"项目，为定价策略提供成本基准。
* **实现方式**: `devops_collector/sql/FINANCE_ANALYTICS.sql` (`view_finance_project_profitability`)

### 4.2 里程碑交付与回款健康度 (Milestone-Payment Health) 🌟 (New)

* **核心逻辑**: 监控技术交付进度与财务回款节奏的同步性。

* **价值**: 预警现金流断裂风险，为财务部门提供精准的现金流预测。
* **实现方式**: `devops_collector/sql/FINANCE_ANALYTICS.sql` (`view_finance_milestone_payment_health`)

### 4.3 人力成本燃烧率与预算预警 (Burn Rate Alert) 🌟 (New)

* **核心逻辑**: 监控项目的人力成本消耗速度与预算健康度。
  * **燃烧率**: 月均人力成本消耗速度。
  * **跑道时长**: 剩余预算还能支撑多久。

* **价值**: 提前 2-3 个月预警预算超支。
* **实现方式**: `devops_collector/sql/FINANCE_ANALYTICS.sql` (`view_finance_burn_rate_alert`)

### 4.4 技术债务的财务量化 (Tech Debt Cost) 🌟 (New)

* **核心逻辑**: 将 SonarQube 的技术债务转换为财务成本。

* **价值**: 用 CFO 听得懂的语言（金额）量化技术债务，为重构项目争取预算。
* **实现方式**: `devops_collector/sql/FINANCE_ANALYTICS.sql` (`view_finance_tech_debt_cost`)

### 4.5 外包 vs 自研的成本效益分析 (Outsourcing Analysis) 🌟 (New)

* **核心逻辑**: 对比外包项目与自研项目的成本与质量。

* **价值**: 为"外包 vs 自研"决策提供量化依据。
* **实现方式**: `devops_collector/sql/FINANCE_ANALYTICS.sql` (`view_finance_outsourcing_analysis`)

### 4.6 研发资本化合规性监控 (CAPEX Compliance) 🌟 (New)

* **核心逻辑**: 识别可资本化的研发投入，确保会计合规。
  * **资本化**: Feature/Epic 类工时。
  * **费用化**: Bug/Refactor 类工时。

* **价值**: 降低财务审计风险，优化财务报表。
* **实现方式**: `devops_collector/sql/FINANCE_ANALYTICS.sql` (`view_finance_capex_compliance`)

---

## 🛡️ 5. 内控与合规性洞察 (Compliance Analytics)

### 5.1 四眼原则合规性监控 (Four-Eyes Principle) 🌟 (New)

* **核心逻辑**: 确保代码合并经过独立审查，满足 SOX 404 职责分离要求。

* **价值**: 降低代码质量风险，为审计提供合规证据。
* **实现方式**: `devops_collector/sql/COMPLIANCE_ANALYTICS.sql` (`view_compliance_four_eyes_principle`)

### 5.2 权限滥用与异常操作检测 (Privilege Abuse) 🌟 (New)

* **核心逻辑**: 识别非工作时间的敏感操作和权限滥用行为。

* **价值**: 识别内部威胁，满足 ISO 27001 访问控制要求。
* **实现方式**: `devops_collector/sql/COMPLIANCE_ANALYTICS.sql` (`view_compliance_privilege_abuse`)

### 5.3 变更管理合规性追溯 (Change Traceability) 🌟 (New)

* **核心逻辑**: 确保生产变更可追溯到需求，满足 ITIL 变更管理要求。

* **价值**: 为事故调查提供审计线索，降低合规风险。
* **实现方式**: `devops_collector/sql/COMPLIANCE_ANALYTICS.sql` (`view_compliance_change_traceability`)

### 5.4 敏感数据访问审计 (Sensitive Data Access) 🌟 (New)

* **核心逻辑**: 监控敏感文件的访问和变更，满足 GDPR/PIPL 数据保护要求。

* **价值**: 预防密钥泄露事故，为安全审计提供证据。
* **实现方式**: `devops_collector/sql/COMPLIANCE_ANALYTICS.sql` (`view_compliance_sensitive_data_access`)

### 5.5 职责分离有效性验证 (Segregation of Duties) 🌟 (New)

* **核心逻辑**: 确保同一人不同时拥有开发和发布权限，满足 SOX 404 要求。

* **价值**: 降低舞弊风险，为内审提供合规证据。
* **实现方式**: `devops_collector/sql/COMPLIANCE_ANALYTICS.sql` (`view_compliance_segregation_of_duties`)

### 5.6 开源许可证合规性扫描 (OSS License Risk) 🌟 (New)

* **核心逻辑**: 基于 OWASP Dependency-Check 扫描项目依赖，识别高风险开源许可证。
  * **SPDX 标准化**: 将许可证规范化为 SPDX ID（如 Apache-2.0, MIT, GPL-3.0）。
  * **风险评级**: 预置 16+ 常见许可证规则，自动评估风险等级。
  * **CVE 漏洞检测**: 同时识别依赖包的安全漏洞（CVSS 评分）。

* **价值**: 降低知识产权诉讼风险，满足企业开源治理政策，为法务部门提供风险清单。
* **实现方式**:
  * SQL: `devops_collector/sql/COMPLIANCE_ANALYTICS.sql` (`view_compliance_oss_license_risk_enhanced`)
  * Worker: `devops_collector/plugins/dependency_check/worker.py`
  * 数据表: `dependency_scans`, `dependencies`, `dependency_cves`, `license_risk_rules`

### 5.7 代码归属与知识产权保护 (IP Protection) 🌟 (New)

* **核心逻辑**: 识别离职员工的异常行为和潜在的知识产权流失风险。

* **价值**: 预防知识产权流失，为法律诉讼提供证据。
* **实现方式**: `devops_collector/sql/COMPLIANCE_ANALYTICS.sql` (`view_compliance_ip_protection`)

---

## 🏗️ 4. 技术架构总结 (Architecture Summary)

### 4.1 技术栈

* **开发语言**: Python 3.9+ (强类型注解)
* **核心框架**: 异步 Worker 模式，使用 **RabbitMQ** 进行任务分发。
* **消息队列**: RabbitMQ (负责任务并发处理、解耦与重试)
* **ORM 层**: SQLAlchemy (Declarative Mapping)
* **数据库**: PostgreSQL (生产环境推荐)
* **依赖管理**: `requirements.txt` (tenacity, requests, sqlalchemy, psycopg2, pika)
* **工程标准 (Engineering Standards)**: 🌟 (New)
  * **深度 AI 集成**: 核心业务 (AC-to-Steps) 由 LLM 驱动，支持 [ai] 节段式配置。
  * **Pydantic V2 架构**: 全量采用 V2 特性（`from_attributes`, `field_validator`, `validation_alias`），实现零拷贝的 ORM 映射。
  * **数据模型标准化**: 参照 Google Python Style Guide 完成了 11 个模型模块的重构，包含全量 Docstrings 和 `__repr__` 调试支持。
  * **Google Python Style**: 核心代码遵循 Google 风格指南，包含严格的 Docstrings 规范。

### 4.2 架构分层

1. **采集层**: `plugins/` 目录，封装 API Client，实现数据拉取与适配。
2. **调度层**: `scheduler.py`，基于时间策略生成同步任务。
3. **Worker 层**: `worker.py`，消费 MQ 消息，执行具体插件逻辑。
4. **模型层**: `models/` 目录，定义星型数据库模式，确保数据一致性。
5. **模型层**: `models/` 目录，定义星型数据库模式，确保数据一致性。
6. **数据层**: SQL Views (位于 `sql/` 目录)，提供分析就绪的数据宽表与集市。
7. **基础设施**: **Docker & Make**，实现了“代码即基础设施 (IaC)”的标准化交付，屏蔽环境差异。

---

## 📘 5. 操作手册 (Operational Manual)

### 5.1 环境部署 (Deployment)

本项目推荐使用 **Docker + Make** 进行标准化部署，无需手动安装 Python 环境。

1. **准备配置文件**:

    ```bash
    cp .env.example .env
    # 编辑 .env 文件，填入：
    # - 数据库密码 (POSTGRES_PASSWORD)
    # - GitLab/SonarQube/Jenkins 凭证 (如 GITLAB__TOKEN)
    ```

2. **一键部署**:

    ```bash
    # 方式 A: 傻瓜式部署脚本 (推荐 Linux/Mac 服务器)
    chmod +x deploy.sh
    ./deploy.sh

    # 方式 B: Make 命令 (生产模式)
    make deploy-prod

    # 方式 C: 开发调试 (本地环境)
    make deploy
    ```

    此命令将自动执行：
    * 构建 Docker 镜像 (`docker-compose build`)
    * 启动所有容器 (`docker-compose up -d`)
    * 等待数据库健康检查通过
    * 执行初始化脚本 (`scripts/init_*.py`)

### 5.2 常用运维命令

所有操作建议通过 `make` 命令在容器内执行，以确保环境一致性。

* **查看日志**: `make logs`
* **停止服务**: `make down`
* **手动全量同步**: `make sync-all`
* **进入容器 Shell**: `make shell` (用于调试)

### 5.3 数据视图更新

默认 `make deploy` 已包含初始数据加载。如果需要手动重新加载 SQL 视图：

```bash
docker-compose exec -T db psql -U postgres -d devops_db -f /app/devops_collector/sql/PROJECT_OVERVIEW.sql
# ...
```

### 5.4 执行数据采集

系统分为 Scheduler (调度) 和 Worker (执行) 两部分，均已容器化运行。

**手动触发一次全量同步**:

```bash
make sync-all
```

此命令会在容器内依次运行调度器生成任务，并在 Worker 中处理这些任务。

**查看后台服务状态**:

```bash
docker-compose ps
```

### 5.4 独立脚本工具

* **手动同步 SonarQube**: `python scripts/sonarqube_stat.py`
* **手动验证 Jenkins**: `python scripts/verify_jenkins_plugin.py`
* **数据逻辑验证**: `python scripts/verify_logic.py`
* **数据逻辑重算**: `python scripts/reprocess_staging_data.py` (基于 Staging 数据回放)

### 5.6 系统验证与仿真测试 (Validation & Simulation)

系统内置了“七位一体”全链路仿真测试框架，允许在脱离真实环境的情况下验证从 API 到指标计算的完整逻辑。

**功能特性**:

* **多源 API 仿真**: 同时拦截并模拟 **GitLab, SonarQube, Jenkins, Jira, ZenTao, Nexus, JFrog** 七个系统的 Rest API 响应。
* **内存流水线**: 采用 SQLite 内存数据库，支持 50+ 张模型表的自动构建与跨系统一致性校验。
* **关联路径验证**: 验证从“代码提交”到“构建任务”再到“制品产出”的端到端逻辑链路。

**执行方式**:

```bash
# 执行全链路集成仿真测试 (七系统联合)
python tests/simulations/run_full_integration.py

# 执行制品库专项仿真 (Nexus + JFrog)
python tests/simulations/run_artifactory_integration.py

# 执行敏捷/管理专项仿真 (Jira + ZenTao)
python tests/simulations/run_jira_integration.py

# 执行异常场景与容错重试仿真
python tests/simulations/run_error_scenarios.py
```

---

### 5.7 服务台部署 (Service Desk Deployment)

* **前置条件**: 确保 `auth` 模块已启用，数据库已执行 `alembic upgrade head` (或初始化脚本) 以创建 User/AuthToken 表。
* **静态资源**: 将 `devops_portal/static/` 下的 HTML 文件部署至 Nginx 或直接通过 FastAPI StaticFiles 挂载（默认路径 `/static`）。
* **环境变量**: 确保 `SECRET_KEY` 已设置，用于 JWT 签名。

---

## 🔮 6. 未来规划 (Roadmap)

* **BI 大屏集成**: 计划提供 Superset Dashboard 模板，一键导入上述 SQL 视图的可视化。
* **分布式采集加速**: 引入 Celery + Redis 替换当前简单的 Pika 模式，支持海量数据的并发抓取。
* **Web 管理端**: 基于 FastAPI 开发轻量级管理后台，用于手动修正用户归属和查看同步状态。
* **实时 Webhook**: 增加对各工具 Webhook 的支持，实现从“周期性同步”到“事件驱动更新”的转换。

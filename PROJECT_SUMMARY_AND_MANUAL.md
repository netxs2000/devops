# DevOps Data Collector - 项目总结与系统功能手册

**版本**: 3.2.0
**日期**: 2025-12-18
**维护**: DevOps 效能平台团队

---

## 📚 1. 项目综述 (Project Overview)

### 1.1 背景与目标
在现代软件研发过程中，研发数据分散在不同的工具链中（如 GitLab 管理代码与过程，SonarQube 管理质量），形成了数据孤岛。**DevOps Data Collector** 旨在解决这一痛点，通过构建统一的数据采集与分析平台，将分散的研发数据聚合为企业级资产。

### 1.2 核心价值
1.  **打通数据孤岛**: 统一 GitLab、SonarQube 和 Jenkins 数据，实现开发、质量与构建的关联分析。
2.  **统一身份认证**: 解决工具间账号不一致问题，通过邮箱自动聚合“自然人”在不同系统的活动。
3.  **效能度量标准化**: 自动化计算 DORA 指标（部署频率、变更前置时间等），为研发效能改进提供数据支撑。
4.  **战略与风险洞察**: 通过波士顿矩阵和风险看板，提供从 CTO 到 PMO 的战略决策支持。

---

## 🛠️ 2. 系统功能手册 (System Function Manual)

### 2.1 多源数据采集 (Multi-Source Collection)
系统采用**插件化架构**，支持多种数据源的扩展。

#### 2.1.1 GitLab 采集插件
*   **元数据同步**: 自动同步项目名称、描述、Star 数、Fork 数等。
*   **代码提交 (Commits)**:
    *   采集 Commit 基础信息（作者、时间、Message）。
    *   **深度 Diff 分析**: 使用 `DiffAnalyzer` 自动拆解代码变更，区分**有效代码行**、**注释行**和**空行**，通过 `commit_file_stats` 表记录文件级明细。
*   **合并请求 (Merge Requests)**: 记录 MR 状态、评审人、合并时间，用于计算 CR 耗时。
*   **流水线与部署 (CI/CD)**:
    *   采集 Pipeline 状态与时长。
    *   采集 Deployment 记录（环境、Ref），作为 **DORA 指标**的核心数据源。
*   **过程数据**: 采集 Issue（需求/缺陷）和 Notes（评论），支持沟通密度分析。
*   **CALMS 深度扫描 (New)**: 自动采集 Issue 的 **State/Label/Milestone Resource Events**。通过追踪这些原子事件，系统能够量化“等待浪费”、“需求跳变频率”以及“跨团队响应速度”，为组织文化扫描提供核心依据。
*   **工程卓越度增强**: 自动计算 MR 的**评审轮次 (Review Cycles)**、**有效评论数**、**代码规范状态 (Lint)** 以及**非工作时间提交频率 (Work-Life Balance)**。
*   **制品与依赖扫描**: 同步 GitLab Package Registry 中的制品元数据，并自动建立跨项目的模块依赖图谱。
*   **共享文化 (Sharing)**: 采集 Wiki 变更频率，作为知识库活跃度（Sharing 维度）的度量。

#### 2.1.2 SonarQube 采集插件
*   **自动映射**: 基于项目路径规则自动关联 GitLab 项目与 SonarQube 项目。
*   **质量快照**: 周期性拉取代码覆盖率 (Coverage)、技术债务 (Tech Debt)、Bug 数等指标，存入 `sonar_measures`。
*   **趋势记录**: 记录质量随时间的变化趋势，支持历史回溯。
*   **Issue 同步 (可选)**: 支持同步具体的代码异味、Bug 和漏洞详情（默认关闭，可通过配置开启）。

#### 2.1.3 Jenkins 采集插件
*   **任务发现 (Job Discovery)**: 自动同步 Jenkins 实例中的所有 Job 列表及其元数据。
*   **构建历史 (Builds)**: 
    *   采集构建状态 (Result)、耗时 (Duration)、时间戳。
    *   **触发源分析**: 识别构建是由 SCM 变更、用户手动、还是定时任务触发。
*   **跨系统映射**: 自动通过 Job 名称匹配 GitLab 项目路径，建立构建与代码库的血缘关系。
*   **增量同步**: 自动记录同步断点，仅拉取最新的构建记录，支持大规模任务同步。

#### 2.1.4 Jira 采集插件 (New)
*   **敏捷实体同步**: 完整拉取项目 (Project)、看板 (Board)、迭代 (Sprint) 和问题 (Issue)。
*   **变更历史 (Changelog)**: 记录状态流转过程（如 To Do -> In Progress），支持计算周期时间 (Cycle Time)。
*   **工作负载分析**: 统计 Assignee 分布，支持 HR 维度的资源投入分析。

#### 2.1.5 禅道 (ZenTao) 采集插件
*   **全量生命周期**: 采集产品 (Product)、计划 (Plan)、需求 (Story) 和执行 (ExecutionInstance)。
*   **结构化映射**: 将禅道内部复杂的层级关系映射为统一的 Issue 模型，确保跨源数据统计的一致性。

#### 2.1.6 Nexus 采集插件 (New)
*   **资产普查**: 自动同步 Nexus 仓库中的组件 (Components) 与资产 (Assets)。
*   **校验和记录**: 采集 SHA1/SHA256 校验和，为软件包的唯一性验证提供支持。

#### 2.1.7 JFrog Artifactory 采集插件 (New)
*   **制品追溯**: 基于 AQL (Artifactory Query Language) 采集制品元数据。
*   **质量与安全**: 同步下载量统计 (Stats) 和 Xray 安全扫描摘要 (Vulnerabilities)。
*   **构建血缘**: 自动提取制品属性中的 `build.name`，实现从制品回溯到构建任务的完整链路。

### 2.2 智能数据处理 (Intelligent Processing)

#### 2.2.1 统一身份归一化 (Identity Matcher)
*   **独立模块化**: 已重构为独立模块 `IdentityMatcher` 和 `UserResolver`，支持跨插件调用。
*   **自动匹配**: 系统内置智能匹配引擎，优先基于 **Email** 将 Git 提交记录关联到全局 `users` 表。
*   **模糊匹配**: 支持基于 Name 或 Username 前缀的辅助匹配策略。
*   **虚拟账号管理**: 自动标记无公司邮箱的外部贡献者，支持后续手工归并。

#### 2.2.2 插件工厂与实例化 (Plugin Factory) (New)
*   **零耦合分发**: 主 Worker 进程通过 `PluginRegistry` 动态创建 Client 和 Worker 实例，彻底消除 `if-elif` 硬编码。
*   **统一配置路由**: 任务根据 `source` 类型自动关联 `config.ini` 中的对应配置项。

#### 2.2.3 断点续传与增量同步 (Resumable Sync)
*   **状态机**: 每个项目维护 `content_status` (PENDING/SYNCING/COMPLETED)。
*   **从断点恢复**: 记录同步进度（如 Page Number 或 Last Synced Time），中断后重新运行通过 `sync_state` 自动接续，无需从头重跑。
*   **Generator 流式处理**: 客户端采用 `yield` 模式逐页拉取数据，结合 `batch save` 自定义批处理，有效防止大规模项目同步时的内存溢出 (OOM)。

*   **层级构建**: 将 Group/Subgroup 映射为标准的四级组织架构，支持部门层级的效能聚合查询。

#### 2.2.4 跨系统映射逻辑 (Cross-System Mapping) (New)
系统通过“约定优于配置”的原则打通不同工具链的数据：
*   **SonarQube -> GitLab**: 默认基于 SonarQube 的 `Project Key` 或 `Project Name` 匹配 GitLab 的 `path_with_namespace`。
*   **Jenkins -> GitLab**: 基于 Jenkins Job 的 `fullName` 或 `name` 与 GitLab 项目名称进行模糊及完全匹配。
*   **Jira -> GitLab**: 通过关联配置或项目 Key 的命名规范实现双向追踪。
*   **制品库 -> 构建/代码**: 
    *   **JFrog**: 通过 `build.name` 属性自动关联至对应的 `jenkins_jobs`。
    *   **Nexus**: 基于 Maven GAV (GroupId, ArtifactId) 坐标与 GitLab 项目路径的命名契约进行关联。
*   **核心关联健**: 统一指向 `projects.id`，实现“一个项目，全链洞察”。

#### 2.2.5 容错与自动重试 (Fault Tolerance & Retry) (New)
系统内置了工业级的异常处理与重试机制，确保在复杂网络环境下的高可用性：
*   **智能重试策略**: 基于 `tenacity` 实现指数退避重试（Exponential Backoff）。
*   **精细化异常分类**: 
    *   **可重试异常**: 如网络超时、连接断开、5xx 服务端错误、429 速率限制。
    *   **非重试异常**: 如 401/403 认证错误，系统将立即停止并记录 ERROR 日志，防止无效重试。
*   **速率限制适配**: 自动解析 API 返回的 `Retry-After` 头部，动态调整等待时间。

---

## 📊 3. 深度洞察与分析 (Advanced Analytics)

本系统内置了多维度分析体系，从**效能、质量、协作、价值、行为、架构、战略**七个维度全面量化研发过程。

### 3.1 研发效能 DORA 指标 (DORA Metrics)
- **核心逻辑**: 通过四个关键指标量化软件交付绩效，平衡“速度”与“稳定性”。
- **价值**: 对标业界标准 (DevOps Research and Assessment)，持续监控并优化研发交付链条的效率与质量。
- **维度**:
    - **部署频率 (Deployment Frequency)**: 成功部署到生产环境的频率。
    - **变更前置时间 (Lead Time for Changes)**: 代码从提交 (Commit) 到部署至生产环境 (Deploy) 的时长。
    - **变更失败率 (Change Failure Rate)**: 导致失败/回滚或需要热修复的部署占比。
    - **平均恢复时间 (Time to Restore Service)**: 发生生产故障后恢复服务所需的平均时间 (MTTR)。
- **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql` (Dept Ranking)

### 3.2 个人综合贡献度 (User Impact Score)
- **核心逻辑**: 摒弃单一的“代码行数”评价，构建涵盖代码产出、团队协作、问题解决的多维度加权评分模型。
- **价值**: 公平量化开发者产出，避免单一指标偏颇，引导高质量的工程行为。
- **维度**:
    - **代码产出**: `Commits Count`, `Lines Added` (净增)。
    - **协作贡献**: `Merge Requests Merged` (核心产出), `Merge Requests Opened`。
    - **问题管理**: `Issues Resolved` (解决), `Issues Reported` (发现)。
- **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.3 项目价值评估 (Project Value Index)
- **核心逻辑**: 结合活跃度、规模、稳定性、协作度构建多维度的项目价值指数。
- **价值**: 识别核心资产与僵尸项目，通过 `value_score` 进行量化分级，辅助资源投入决策。
- **维度**:
    - **活跃度 (Activity)**: `active_days`。
    - **规模 (Scale)**: `commit_count` + `storage_size`。
    - **稳定性 (Stability)**: `tags_count`。
- **实现方式**: `devops_collector/sql/PROJECT_OVERVIEW.sql`

### 3.4 部门级平衡记分卡 (Department Scorecard)
- **核心逻辑**: 从交付、活力、质量三个维度横向对比各中心/部门表现。
- **价值**: 识别部门间的能力差异，发现管理短板，推动组织效能对齐。
- **维度**:
    - **交付效能**: DORA 四项指标部门均值。
    - **组织活力**: 人均产出 (Commit/MR per Person), 活跃人力占比。
    - **资产质量**: 维护代码总量, Bug 密度。
- **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql`

### 3.5 战略对齐 (OKR & Alignment) (New)
- **核心逻辑**: 将底层研发交付指标 (API 调用量、构建频率等) 向上映射至业务目标 (Objective)。
- **价值**: 让技术产出变得“可理解”，量化技术对业务目标的实际贡献。
- **维度**: 目标进度百分比, KR 信心指数。

### 3.6 成本与 ROI (FinOps) (New)
- **核心逻辑**: 结合服务器/云成本与人力工时成本，计算产研投入产出比。
- **价值**: 优化资源配置，识别长尾低价值项目。
- **维度**: 单位 Story 交付成本, 部门月度云资源开销趋势。

### 3.7 开发者代码热力图 (User Heatmap)
- **核心逻辑**: 可视化展示开发者每日的提交频率 (Contribution Graph)。
- **价值**: 直观呈现开发者的工作节奏与活跃模式。
- **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.6 开发者全生命周期 (User Lifecycle)
- **核心逻辑**: 基于首次和最后一次提交时间，计算人员在职/活跃周期及留存状态。
- **价值**: 辅助 HR 和团队 Lead 分析人才留存率 (Retention) 和流失风险。
- **维度**:
    - **活跃跨度**: `active_days_count` (Last - First)。
    - **当前状态**: `status` (Active/Dormant/Churned)。
- **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.7 开发者技术广度 (Tech Stack Breadth)
- **核心逻辑**: 通过分析代码提交文件的后缀名，识别开发者掌握的编程语言种类与分布。
- **价值**: 识别团队中的 **全栈工程师** (Full Stack) 或跨语言技术专家。
- **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.8 代码评审影响力 (Code Review Impact)
- **核心逻辑**: 仅仅写代码是不够的，**评审他人代码**是高级工程师的重要职责。
- **价值**: 识别团队中的 **技术把关人** (Gatekeeper) 和乐于指导新人的 **导师** (Mentor)。
- **维度**:
    - **评审参与度**: `mrs_reviewed_count`。
    - **交互强度**: `avg_comments_per_review`。
- **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.9 版本发布分析 (Release Analytics)
- **核心逻辑**: 以 Tag 为里程碑，自动划定“版本区间”，统计每个版本包含的提交量和贡献者阵容。
- **价值**: 自动生成“Release Notes”的核心数据，回顾每个版本的开发体量。
- **实现方式**: `devops_collector/sql/PROJECT_OVERVIEW.sql`

### 3.10 代码构成分析 (Code Composition)
- **核心逻辑**: 通过重建代码历史，还原项目当前的文件构成。
- **价值**: 无需 Clone 代码库即可分析项目的技术栈分布 (Python vs Go)、文件规模分布等。
- **实现方式**: `devops_collector/sql/PROJECT_OVERVIEW.sql`

### 3.11 协作熵与评审质量 (Review Quality)
- **核心逻辑**: 区分评审是“走过场”还是“真探讨”，分析代码合并权限的分布。
- **价值**: 提升代码审查的实效性，避免形式主义。
- **维度**:
    - **评审乒乓指数**: Review Rounds (交互轮次)。
    - **评审民主度**: Merger Gini Coefficient (合并权限分布)。

### 3.12 团队倦怠雷达 (Burnout Radar)
- **核心逻辑**: 利用时间戳数据感知团队健康度，寻找不可持续工作的信号。
- **价值**: 提前感知团队的过度劳累，预防人才流失。
- **维度**:
    - **WLB 指数**: 工作时间外及周末的提交占比。
    - **冲刺后遗症**: 密集提交期（如发版前）之后紧接着的 Bug 率。
- **实现方式**: `devops_collector/sql/HR_ANALYTICS.sql`

### 3.13 隐性工作与流程偏离 (Process Deviation)
- **核心逻辑**: 捕捉未被正规管理流程 (Jira/Issue) 覆盖的工作，以及被遗忘的库存。
- **维度**:
    - **游离代码率**: 未关联 Issue 的提交占比。
    - **幽灵分支**: 沉睡超过 30 天且未合并的分支。

### 3.14 代码演进与架构熵 (Code Evolution)
- **核心逻辑**: 分析代码变更的性质（重构 vs 新增）及模块间的隐性依赖。
- **维度**:
    - **重构比率**: 删除线/新增线 趋近于 1。
    - **逻辑耦合热度**: Co-change Frequency (异构模块同时修改)。

### 3.15 跨边界协作力 (InnerSource Impact)
- **核心逻辑**: 衡量组织内部的开源文化与知识共享情况。
- **价值**: 打破部门墙，促进技术复用。
- **维度**:
    - **内源贡献率**: 对非本部门项目的贡献占比。
    - **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql`

### 3.16 战略投资组合 (Strategic Portfolio) (New)
- **核心逻辑**: 基于波士顿矩阵，将项目划分为 Stars (高质高产), Cash Cows (高质低产), Dogs (低质低产), Problem Children (低质高产)。
- **价值**: 辅助 CTO 进行研发资源分配决策。
- **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql`

### 3.17 风险与合规治理 (Governance & Risk) (New)
- **核心逻辑**: 监控 Direct Push (绕过流程) 和 Security Blockers (安全债务)。
- **价值**: 确保研发流程合规，降低生产风险。
- **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql`

### 3.18 投入产出效能 (ROI Efficiency) (New)
- **核心逻辑**: 计算研发投入 (FTE, Hours) 与产出 (Throughput) 的转化率。
- **价值**: 回答 "钱花得值不值"。
- **实现方式**: `devops_collector/sql/PMO_ANALYTICS.sql`

---

## 🏗️ 4. 技术架构总结 (Architecture Summary)

### 4.1 技术栈
*   **开发语言**: Python 3.9+ (强类型注解)
*   **核心框架**: 异步 Worker 模式，使用 **RabbitMQ** 进行任务分发。
*   **消息队列**: RabbitMQ (负责任务并发处理、解耦与重试)
*   **ORM 层**: SQLAlchemy (Declarative Mapping)
*   **数据库**: PostgreSQL (生产环境推荐)
*   **依赖管理**: `requirements.txt` (tenacity, requests, sqlalchemy, psycopg2, pika)

### 4.2 架构分层
1.  **采集层**: `plugins/` 目录，封装 API Client，实现数据拉取与适配。
2.  **调度层**: `scheduler.py`，基于时间策略生成同步任务。
3.  **Worker 层**: `worker.py`，消费 MQ 消息，执行具体插件逻辑。
4.  **模型层**: `models/` 目录，定义星型数据库模式，确保数据一致性。
5.  **数据层**: SQL Views (位于 `sql/` 目录)，提供分析就绪的数据宽表与集市。

---

## 📘 5. 操作手册 (Operational Manual)

### 5.1 环境部署
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置文件
cp devops_collector/config.ini.example devops_collector/config.ini
# 编辑 config.ini 填入 GitLab/SonarQube 的 URL 和 Token
```

### 5.2 初始化系统与数据视图
首次运行前，必须执行初始化脚本以建立表结构，并**部署分析视图**：
```bash
# 1. 初始化数据库与组织架构
python scripts/init_discovery.py

# 2. 部署 SQL 分析视图 (需安装 psql 客户端)
psql -d devops_db -f devops_collector/sql/PROJECT_OVERVIEW.sql
psql -d devops_db -f devops_collector/sql/PMO_ANALYTICS.sql
psql -d devops_db -f devops_collector/sql/HR_ANALYTICS.sql
psql -d devops_db -f devops_collector/sql/TEAM_ANALYTICS.sql
```

### 5.3 执行数据采集
系统分为 Scheduler (调度) 和 Worker (执行) 两部分。

**启动调度器 (Scheduler)**:
定时扫描数据库，生成任务投递到 MQ。
```bash
python -m devops_collector.scheduler
```

**启动工作进程 (Worker)**:
消费 MQ 任务执行实际采集。可启动多个 Worker 进程以并发处理。
```bash
python -m devops_collector.worker
```

### 5.4 独立脚本工具
*   **手动同步 SonarQube**: `python scripts/sonarqube_stat.py`
*   **手动验证 Jenkins**: `python scripts/verify_jenkins_plugin.py`
*   **数据逻辑验证**: `python scripts/verify_logic.py`

### 5.6 系统验证与仿真测试 (Validation & Simulation)
系统内置了“七位一体”全链路仿真测试框架，允许在脱离真实环境的情况下验证从 API 到指标计算的完整逻辑。

**功能特性**:
- **多源 API 仿真**: 同时拦截并模拟 **GitLab, SonarQube, Jenkins, Jira, ZenTao, Nexus, JFrog** 七个系统的 Rest API 响应。
- **内存流水线**: 采用 SQLite 内存数据库，支持 50+ 张模型表的自动构建与跨系统一致性校验。
- **关联路径验证**: 验证从“代码提交”到“构建任务”再到“制品产出”的端到端逻辑链路。

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

## 🔮 6. 未来规划 (Roadmap)
*   **BI 大屏集成**: 计划提供 Superset Dashboard 模板，一键导入上述 SQL 视图的可视化。
*   **分布式采集加速**: 引入 Celery + Redis 替换当前简单的 Pika 模式，支持海量数据的并发抓取。
*   **Web 管理端**: 基于 FastAPI 开发轻量级管理后台，用于手动修正用户归属和查看同步状态。
*   **实时 Webhook**: 增加对各工具 Webhook 的支持，实现从“周期性同步”到“事件驱动更新”的转换。

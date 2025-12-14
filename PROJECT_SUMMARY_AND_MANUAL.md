# DevOps Data Collector - 项目总结与系统功能手册

**版本**: 2.2.0
**日期**: 2025-12-15
**维护**: DevOps 效能平台团队

---

## 📚 1. 项目综述 (Project Overview)

### 1.1 背景与目标
在现代软件研发过程中，研发数据分散在不同的工具链中（如 GitLab 管理代码与过程，SonarQube 管理质量），形成了数据孤岛。**DevOps Data Collector** 旨在解决这一痛点，通过构建统一的数据采集与分析平台，将分散的研发数据聚合为企业级资产。

### 1.2 核心价值
1.  **打通数据孤岛**: 统一 GitLab 和 SonarQube 数据，实现代码提交与代码质量的关联分析。
2.  **统一身份认证**: 解决工具间账号不一致问题，通过邮箱自动聚合“自然人”在不同系统的活动。
3.  **效能度量标准化**: 自动化计算 DORA 指标（部署频率、变更前置时间等），为研发效能改进提供数据支撑。
4.  **组织架构透视**: 支持四级组织架构（公司-中心-部门-小组），实现从团队到个人的层级化效能分析。

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

#### 2.1.2 SonarQube 采集插件
*   **自动映射**: 基于项目路径规则自动关联 GitLab 项目与 SonarQube 项目。
*   **质量快照**: 周期性拉取代码覆盖率 (Coverage)、技术债务 (Tech Debt)、Bug 数等指标，存入 `sonar_measures`。
*   **趋势记录**: 记录质量随时间的变化趋势，支持历史回溯。
*   **Issue 同步 (可选)**: 支持同步具体的代码异味、Bug 和漏洞详情（默认关闭，可通过配置开启）。

### 2.2 智能数据处理 (Intelligent Processing)

#### 2.2.1 统一身份归一化 (Identity Matcher)
*   **自动匹配**: 系统内置智能匹配引擎，优先基于 **Email** 将 Git 提交记录关联到全局 `users` 表。
*   **模糊匹配**: 支持基于 Name 或 Username 前缀的辅助匹配策略。
*   **虚拟账号管理**: 自动标记无公司邮箱的外部贡献者，支持后续手工归并。

#### 2.2.2 断点续传与增量同步 (Resumable Sync)
*   **状态机**: 每个项目维护 `content_status` (PENDING/SYNCING/COMPLETED)。
*   **从断点恢复**: 记录同步进度（如 Page Number 或 Last Synced Time），中断后重新运行通过 `sync_state` 自动接续，无需从头重跑。
*   **Generator 流式处理**: 客户端采用 `yield` 模式逐页拉取数据，结合 `batch save` 自定义批处理，有效防止大规模项目同步时的内存溢出 (OOM)。

#### 2.2.3 组织架构映射 (Organization Mapping)
*   **自动发现**: 启动时自动扫描 GitLab 顶层 Group 结构。
*   **层级构建**: 将 Group/Subgroup 映射为标准的四级组织架构，支持部门层级的效能聚合查询。

---

## 📊 3. 深度洞察与分析 (Advanced Analytics)

本系统内置了多维度分析体系，从**效能、质量、协作、价值、行为、架构**六个维度全面量化研发过程。

### 3.1 研发效能 DORA 指标 (DORA Metrics)
- **核心逻辑**: 通过四个关键指标量化软件交付绩效，平衡“速度”与“稳定性”。
- **价值**: 对标业界标准 (DevOps Research and Assessment)，持续监控并优化研发交付链条的效率与质量。
- **维度**:
    - **部署频率 (Deployment Frequency)**:
        - **说明**: 成功部署到生产环境的频率。
        - **意义**: 衡量交付吞吐量 (Throughput)。
    - **变更前置时间 (Lead Time for Changes)**:
        - **说明**: 代码从提交 (Commit) 到部署至生产环境 (Deploy) 的时长。
        - **意义**: 衡量交付速度 (Speed)。
    - **变更失败率 (Change Failure Rate)**:
        - **说明**: 导致失败/回滚或需要热修复的部署占比。
        - **意义**: 衡量交付质量 (Quality)。
    - **平均恢复时间 (Time to Restore Service)**:
        - **说明**: 发生生产故障后恢复服务所需的平均时间 (MTTR)。
        - **意义**: 衡量系统韧性 (Stability)。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/dora_metrics.sql`

### 3.2 个人综合贡献度 (User Impact Score)
- **核心逻辑**: 摒弃单一的“代码行数”评价，构建涵盖代码产出、团队协作、问题解决的多维度加权评分模型。
- **价值**: 公平量化开发者产出，避免单一指标偏颇，引导高质量的工程行为。
- **维度**:
    - **代码产出**:
        - **指标**: `Commits Count`, `Lines Added` (净增), `Lines Deleted`。
        - **说明**: 需关注净增量，防止“行数刷分”。
        - **意义**: 基础工作量的体现。
    - **协作贡献**:
        - **指标**: `Merge Requests Merged` (核心产出), `Merge Requests Opened`。
        - **说明**: Merged MR 代表了被团队认可的有效产出。
        - **意义**: 体现团队协作与代码质量。
    - **问题管理**:
        - **指标**: `Issues Resolved` (解决), `Issues Reported` (发现)。
        - **说明**: 参与缺陷治理的情况。
        - **意义**: 体现对产品质量的贡献。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/user_impact.sql`

### 3.3 项目价值评估 (Project Value Index)
- **核心逻辑**: 结合活跃度、规模、稳定性、协作度构建多维度的项目价值指数。
- **价值**: 识别核心资产与僵尸项目，通过 `value_score` 进行量化分级，辅助资源投入决策。
- **维度**:
    - **活跃度 (Activity)**:
        - **指标**: `last_activity_at` 衰减分。
        - **说明**: 如 30 天内有活动为满分，否则指数衰减。
        - **意义**: 评价项目是否仍在维护。
    - **规模 (Scale)**:
        - **指标**: `commit_count` + `storage_size`。
        - **说明**: 代码库的物理量级。
        - **意义**: 评价项目的资产厚度。
    - **稳定性 (Stability)**:
        - **指标**: `tags_count`。
        - **说明**: 版本发布次数。
        - **意义**: 体现价值交付的规律性。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/project_value.sql`

### 3.4 部门级平衡记分卡 (Department Scorecard)
- **核心逻辑**: 从交付、活力、质量三个维度横向对比各中心/部门表现。
- **价值**: 识别部门间的能力差异，发现管理短板，推动组织效能对齐。
- **维度**:
    - **交付效能 (Delivery)**:
        - **指标**: DORA 四项指标部门均值。
        - **说明**: 聚合部门内所有项目的 DORA 数据。
        - **意义**: 评价“快不快”和“稳不稳”。
    - **组织活力 (Vitality)**:
        - **指标**: 人均产出 (Commit/MR per Person), 活跃人力占比。
        - **说明**: 部门内活跃开发者的密度。
        - **意义**: 评价团队是否“饱和”和“积极”。
    - **资产质量 (Quality)**:
        - **指标**: 维护代码总量, Bug 密度。
        - **说明**: 单位代码行数下的 Bug 数。
        - **意义**: 评价管理的“复杂度”和“质量”。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/dept_performance.sql`

### 3.5 开发者代码热力图 (User Heatmap)
- **核心逻辑**: 可视化展示开发者每日的提交频率 (Contribution Graph)。
- **价值**: 直观呈现开发者的工作节奏与活跃模式。
- **维度**:
    - **时间分布**:
        - **指标**: `activity_date` (按天聚合)。
        - **说明**: 记录有代码提交的日期。
        - **意义**: 识别工作日/休息日模式。
    - **活动强度**:
        - **指标**: `commit_count` / `lines_added`。
        - **说明**: 当日的产出量级（颜色深浅）。
        - **意义**: 识别高产出时段。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/user_heatmap.sql`

### 3.6 开发者全生命周期 (User Lifecycle)
- **核心逻辑**: 基于首次和最后一次提交时间，计算人员在职/活跃周期及留存状态。
- **价值**: 辅助 HR 和团队 Lead 分析人才留存率 (Retention) 和流失风险。
- **维度**:
    - **活跃跨度**:
        - **指标**: `active_days_count` (Last - First)。
        - **说明**: 也就是“工龄”或“项目参与时长”。
        - **意义**: 衡量员工稳定性。
    - **当前状态**:
        - **指标**: `status` (Active/Dormant/Churned)。
        - **说明**: >90天无提交视为流失 (Churned)。
        - **意义**: 识别流失风险。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/user_lifecycle.sql`

### 3.7 开发者技术广度 (Tech Stack Breadth)
- **核心逻辑**: 通过分析代码提交文件的后缀名，识别开发者掌握的编程语言种类与分布。
- **价值**: 识别团队中的 **全栈工程师** (Full Stack) 或跨语言技术专家，辅助构建人才技能矩阵。
- **维度**:
    - **语言分布**:
        - **指标**: `language_count`, `skills_list`。
        - **说明**: 统计如 "Python, Vue, Go" 的语言组合。
        - **意义**: 评估技术栈广度。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/user_tech_stack.sql`

### 3.8 代码评审影响力 (Code Review Impact)
- **核心逻辑**: 仅仅写代码是不够的，**评审他人代码**是高级工程师的重要职责。
- **价值**: 识别团队中的 **技术把关人** (Gatekeeper) 和乐于指导新人的 **导师** (Mentor)。
- **维度**:
    - **评审参与度**:
        - **指标**: `mrs_reviewed_count`。
        - **说明**: 参与了多少个 MR 的评审。
        - **意义**: 衡量技术辅导的投入度。
    - **交互强度**:
        - **指标**: `avg_comments_per_review`。
        - **说明**: 平均每个 Review 输出的评论数。
        - **意义**: 是简单 "LGTM" 还是深度探讨。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/user_code_review.sql`

### 3.9 版本发布分析 (Release Analytics)
- **核心逻辑**: 以 Tag 为里程碑，自动划定“版本区间”，统计每个版本包含的提交量和贡献者阵容。
- **价值**: 自动生成“Release Notes”的核心数据，回顾每个版本的开发体量。
- **维度**:
    - **版本规模**:
        - **指标**: `commits_count`, `lines_changed`。
        - **说明**: 两个 Tag 之间的变更量。
        - **意义**: 版本的开发体量。
    - **贡献阵容**:
        - **指标**: `author_list`。
        - **说明**: 参与该版本的开发者名单。
        - **意义**: 明确版本贡献者。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/tag_analytics.sql`

### 3.10 代码构成分析 (Code Composition)
- **核心逻辑**: 通过重建代码历史，还原项目当前的文件构成。
- **价值**: 无需 Clone 代码库即可分析项目的技术栈分布 (Python vs Go)、文件规模分布等。
- **维度**:
    - **文件类型**:
        - **指标**: `extension`, `file_count`。
        - **说明**: 各后缀名的文件数量。
        - **意义**: 识别项目技术栈。
    - **有效行数**:
        - **指标**: `total_lines`, `avg_lines_per_file`。
        - **说明**: 代码文件统计总行数；**忽略图片/视频/二进制**。
        - **意义**: 项目规模精准估算。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/extension_stats.sql`

### 3.11 协作熵与评审质量 (Review Quality & Democracy)
- **核心逻辑**: 区分评审是“走过场”还是“真探讨”，分析代码合并权限的分布。
- **价值**: 提升代码审查的实效性，避免形式主义和权力垄断。
- **维度**:
    - **评审乒乓指数 (Ping-Pong Index)**:
        - **指标**: Review Rounds。
        - **说明**: MR 先后被不同人评论和修改的轮次。
        - **意义**: 0 轮代表“橡皮图章” (Rubber Stamp)；>5 轮代表需求不清或过度纠结 (Bike-shedding)。
    - **评审民主度 (Review Democracy)**:
        - **指标**: Merger Gini Coefficient。
        - **说明**: 项目代码合并者 (Merger) 的分布情况。
        - **意义**: 避免“独裁者”模式（只有 Leader 能合并），提倡代码集体所有权。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/review_quality.sql`

### 3.12 团队倦怠雷达 (Burnout Radar)
- **核心逻辑**: 利用时间戳数据感知团队健康度，寻找不可持续工作的信号。
- **价值**: 提前感知团队的过度劳累，预防人才流失。
- **维度**:
    - **WLB 指数 (Work-Life Balance)**:
        - **指标**: Off-hours Commit Ratio。
        - **说明**: 发生在工作时间 (如 9:00-19:00) 之外及周末的提交占比。
        - **意义**: 持续的高异常值是人才流失 (Churn) 的先行指标。
    - **冲刺后遗症 (Post-Crunch Quality Dip)**:
        - **指标**: Post-release Bug Rate。
        - **说明**: 密集提交期（如发版前）之后紧接着的 Bug 率或代码回滚率。
        - **意义**: 量化“赶工”带来的质量反噬和技术债务利息。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/burnout_radar.sql`

### 3.13 隐性工作与流程偏离 (Process Deviation)
- **核心逻辑**: 捕捉未被正规管理流程 (Jira/Issue) 覆盖的工作，以及被遗忘的库存。
- **价值**: 确保需求可追溯性，减少库存浪费。
- **维度**:
    - **游离代码率 (Unmanaged Code)**:
        - **指标**: No-Issue Commit Ratio。
        - **说明**: 直接 Push 且未关联 Issue/Jira ID 的 Commits 占比。
        - **意义**: 量化“失控”的研发流程，确保需求可追溯性。
    - **幽灵分支 (Ghost Branches)**:
        - **指标**: Stale Branch Count。
        - **说明**: 有提交但从未发起 MR，且沉睡超过 30 天的分支。
        - **意义**: 识别未兑现的价值 (Inventory Waste)。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/process_deviation.sql`

### 3.14 代码演进与架构熵 (Code Evolution)
- **核心逻辑**: 分析代码变更的性质（重构 vs 新增）及模块间的隐性依赖。
- **价值**: 指导架构优化与微服务拆分，防止架构腐烂。
- **维度**:
    - **重构比率 (Refactoring Ratio)**:
        - **指标**: Deletion/Addition Ratio。
        - **说明**: *Deleted* / *Added* 趋近于 1 的提交占比。
        - **意义**: 量化团队花在“偿还债务”而非“新建功能”上的精力。
    - **逻辑耦合热度 (Logical Coupling)**:
        - **指标**: Co-change Frequency。
        - **说明**: 经常在同一个 MR 中被同时修改的两个异构模块 (如 `order/` 和 `user/`)。
        - **意义**: 发现架构上的隐性依赖 (Logical Coupling)，作为微服务拆分的依据。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/code_evolution.sql`

### 3.15 跨边界协作力 (InnerSource Impact)
- **核心逻辑**: 衡量组织内部的开源文化与知识共享情况。
- **价值**: 打破部门墙，促进技术复用，消除知识高危点。
- **维度**:
    - **内源贡献率 (InnerSource Rate)**:
        - **指标**: Cross-Dept Contribution Ratio。
        - **说明**: 成员对 **非本部门** 所属项目的贡献占比。
        - **意义**: 衡量打破“部门墙”的能力。
    - **知识孤岛指数 (Silo Index)**:
        - **指标**: Bus Factor / Single Author Path。
        - **说明**: 长期仅由单人维护的文件路径占比。
        - **意义**: 识别高危“独家代码”，提前制定传承计划。
- **实现方式**: `devops_collector/plugins/gitlab/sql_views/innersource.sql`

本系统不仅采集数据，还内置了多维度分析体系，旨在从**效能、质量、协作、价值**四个维度全面量化研发过程。

### 3.1 研发效能 DORA 指标 (DORA Metrics)
通过四个关键指标量化软件交付绩效，平衡“速度”与“稳定性”。
*   **部署频率 (Deployment Frequency)**: 成功部署到生产环境的频率，衡量交付吞吐量。
*   **变更前置时间 (Lead Time for Changes)**: 代码从 Commit 到 Deploy 的时长，衡量交付速度。
*   **变更失败率 (Change Failure Rate)**: 导致回滚或热修复的部署占比，衡量交付质量。
*   **平均恢复时间 (Time to Restore Service)**: 故障发生到恢复的服务时长 (MTTR)，衡量系统韧性。
> **实现原理**: 基于 `deployments` 表与 `commits` 表的时间戳差值计算。

### 3.2 个人综合贡献度 (User Impact Score)
摒弃单一的“代码行数”评价，构建涵盖代码产出、团队协作、问题解决的多维度加权评分模型。
*   **代码产出**: `Commits Count`, `Lines Added` (净增量), `Lines Deleted`。
*   **协作贡献**: `Merge Requests Merged` (核心产出, 权重高), `Merge Requests Opened`。
*   **问题管理**: `Issues Resolved` (解决问题, 权重中), `Issues Reported`。
*   **评审贡献**: `Reviews Conducted` (参与评审), `Comments Value`。
> **价值**: 引导工程师从“写代码”转向“解决问题”和“团队协作”。

### 3.3 项目价值评估 (Project Value Index)
通过活跃度、规模、稳定性等多维度识别核心资产与僵尸项目。
*   **活跃度 (Activity)**: 基于 `last_activity_at` (如30天无提交则衰减)。
*   **规模 (Scale)**: 代码量级 (`loc`) 与历史厚度 (`commit_count`)。
*   **稳定性 (Stability)**: 版本发布频率 (`tags_count`)。
*   **协作 (Collaboration)**: 分支与 MR 活跃度。
*   **投入 (Effort)**: 实际消耗工时 (`total_time_spent`)。

### 3.4 部门级平衡记分卡 (Department Scorecard)
从交付、活力、质量三个维度横向对比各中心/部门表现。
*   **交付效能**: DORA 四项指标部门均值。
*   **组织活力**: 人均产出 (Commit/MR per Person) 与活跃人力占比。
*   **资产规模与质量**: 维护代码总量与 Bug 密度。

### 3.5 开发者画像与行为分析 (User Profiling)
*   **代码热力图 (Heatmap)**: 可视化每日提交频率 (类似 Github Contribution)，呈现工作节奏。
*   **技术广度 (Tech Stack)**: 分析代码文件后缀，识别全栈工程师与专精人才 (如 "Python + Vue")。
*   **全生命周期 (Lifecycle)**: 计算“首次亮相”到“最后活跃”的时间跨度，分析人才留存 (Retention) 与流失 (Churn) 状态。

### 3.6 代码评审影响力 (Code Review Impact)
量化技术把关与导师贡献。
*   **评审参与度**: `mrs_reviewed_count` (Review 数量)。
*   **交互强度**: `avg_comments_per_review` (是简单的 LGTM 还是深度探讨)。
*   **价值**: 识别团队中的“技术把关人” (Gatekeeper)。

### 3.7 版本发布与构成分析 (Release & Composition)
*   **版本发布分析 (Release Logs)**: 以 Tag 为里程碑，统计每个版本包含的 Commits、Contributors 和变更行数，自动生成 Release Notes 数据源。
*   **代码构成 (Extension Analysis)**: 重建文件构成，统计各语言文件数量、行数 (忽略图片/二进制)，无需 Clone 仓库即可分析技术栈。
*   **分支活跃度 (Branch Ops)**: 识别僵尸分支 (Inactive > 90d) 和未合并分支，辅助仓库瘦身。

### 3.8 团队活动时间分析 (Work Rhythm)
*   **工作节奏**: 分析 `hour_of_day` 和 `day_of_week` 分布，识别团队活跃时段与潜在的过度加班 (Weekend commits)。
*   **趋势分析**: 年/月/周的活动趋势图，辅助识别项目冲刺期与休整期。

### 3.9 (新增) 知识孤岛分析 (Bus Factor & Knowledge Silos)
*   **核心逻辑**: 分析各个项目或模块的主要贡献者分布。
*   **指标**: `Top Contributor Ratio` (头部贡献者代码占比)。
*   **价值**: 识别高风险项目（即“那个人走了，没人能维护”的项目），提前制定知识传承计划。

### 3.10 (新增) 代码质量趋势 (Quality Trends)
*   **核心逻辑**: 结合 SonarQube 历史数据。
*   **指标**: 技术债务比率 (Technical Debt Ratio) 变化曲线、新增 Bug 趋势。
*   **价值**: 监控“偿还债务”还是“积累债务”，评估重构效果。

---

### 3.11 协作熵与评审质量 (Review Quality & Democracy)
这也是“行为分析”的重要一环，用于区分评审是“走过场”还是“真探讨”。
*   **评审乒乓指数 (Ping-Pong Index)**:
    *   *定义*: MR 先后被不同人评论和修改的轮次。
    *   *洞察*: 0 轮代表“橡皮图章” (Rubber Stamp)；>5 轮代表需求不清或过度纠结 (Bike-shedding)。
*   **评审民主度 (Review Democracy)**:
    *   *定义*: 项目合并者 (Merger) 的分布情况。
    *   *洞察*: 避免“独裁者”模式（只有 Leader 能合并），提倡代码集体所有权。

### 3.12 团队倦怠雷达 (Burnout Radar)
利用时间戳数据感知团队健康度。
*   **WLB 指数 (Work-Life Balance)**:
    *   *定义*: 发生在工作时间 (如 9:00-19:00) 之外及周末的提交占比。
    *   *洞察*: 持续的高异常值是人才流失 (Churn) 的先行指标。
*   **冲刺后遗症 (Post-Crunch Dip)**:
    *   *定义*: 密集提交期（如发版前）之后紧接着的 Bug 率或代码回滚率。

### 3.13 隐性工作与流程偏离 (Shadow Work)
*   **游离代码率 (Unmanaged Code)**:
    *   *定义*: 直接 Push 且未关联 Issue/Jira ID 的 Commits 占比。
    *   *洞察*: 量化“失控”的研发流程，确保需求可追溯性。
*   **幽灵分支 (Ghost Branches)**:
    *   *定义*: 有提交但从未发起 MR，且沉睡超过 30 天的分支。
    *   *洞察*: 识别未兑现的价值 (Inventory Waste)。

### 3.14 代码演进与架构熵 (Code Evolution)
*   **重构比率 (Refactoring Ratio)**:
    *   *定义*: *Deleted* / *Added* 趋近于 1 的提交占比。
    *   *洞察*: 量化团队花在“偿还债务”而非“新建功能”上的精力。
*   **逻辑耦合热度 (Logical Coupling)**:
    *   *定义*: 经常在同一个 MR 中被同时修改的两个异构模块 (如 `order/` 和 `user/`)。
    *   *洞察*: 发现架构上的隐性依赖，作为微服务拆分的依据。

### 3.15 跨边界协作力 (InnerSource Impact)
*   **内源贡献率**: 成员对 **非本部门** 所属项目的贡献占比。衡量打破“部门墙”的能力。
*   **知识孤岛指数 (Silo Index)**: 长期仅由单人维护的文件路径占比，识别高危“独家代码”。

---

## 🏗️ 4. 技术架构总结 (Architecture Summary)

### 4.1 技术栈
*   **开发语言**: Python 3.9+ (强类型注解)
*   **核心框架**: 无 Web 框架（Worker 模式），专注于 ETL 逻辑。
*   **消息队列**: RabbitMQ (负责任务分发与削峰填谷)
*   **ORM 层**: SQLAlchemy (Declarative Mapping)
*   **数据库**: PostgreSQL (生产环境推荐) / SQLite (开发测试)
*   **依赖管理**: `requirements.txt` (tenacity, requests, sqlalchemy, psycopg2, pika)

### 4.2 架构分层
1.  **采集层**: `plugins/` 目录，封装 API Client，实现数据拉取与适配。
2.  **调度层**: `scheduler.py`，基于时间策略生成同步任务。
3.  **Worker 层**: `worker.py`，消费 MQ 消息，执行具体插件逻辑。
4.  **模型层**: `models/` 目录，定义星型数据库模式，确保数据一致性。
5.  **数据层**: SQL Views (位于 `sql_views/`，逻辑上)，提供分析就绪的数据视图。

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

### 5.2 初始化系统
首次运行前，必须执行初始化脚本以建立表结构和组织树，并发现现有项目：
```bash
python scripts/init_discovery.py
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
*   **数据逻辑验证**: `python scripts/verify_logic.py`
*   **修复验证**: `python scripts/verify_fixes.py`

### 5.5 常见问题排查
*   **同步中断**: 检查日志文件，系统会自动记录失败的项目 ID。重新运行主程序即可自动续传。
*   **RabbitMQ 连接失败**: 检查 `config.ini` 中 MQ 配置及服务状态。
*   **身份未关联**: 检查 `users` 表，确认为用户配置了正确的邮箱。

---

## 🔮 6. 未来规划 (Roadmap)
*   **KPI 报表生成**: 目前仅提供 SQL View，未来可接入 BI 工具 (如 Superset, Grafana) 直接展示。
*   **更多插件**: 计划支持 Jenkins (构建详情)、Jira (敏捷管理) 数据源。
*   **Web 管理端**: 基于 FastAPI 开发轻量级管理后台，用于手动修正用户归属和查看同步状态。

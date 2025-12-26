# PMO 视角 DevInsight 分析方案 (战略与治理)

本文档定义了一套 **战略级 DevOps 效能分析解决方案 (Strategic DevOps Cockpit)**。
旨在帮助 PMO 和 CTO 将视角从单个项目的微观健康，上升到 **项目组合（Portfolio）** 的宏观层面，去回答 **“投入产出比”、“战略一致性”和“宏观风险”** 等核心命题。

这套体系不仅有战术层面的“抓手”（如 DORA 效能、僵尸与合规治理），更具备了 **战略层面的“眼界”**（如波士顿矩阵、跨界创新指数）。
它不仅回答了“我们做得怎么样 (Efficiency)”，更回答了 **“我们是否在做正确的事 (Effectiveness)”** 以及 **“我们的钱花得值不值 (ROI)”**。这是向 CTO 和业务高层汇报的有力武器。

## 1. 核心分析维度 (Strategic Pillars)

本方案构建了支撑研发战略决策的 **九大支柱**：

### 1.1 资源透视 (Resource Allocation)
- **战略拷问**: 我们的精锐部队是否被消耗在低价值的“填坑”中？
- **核心价值**: 识别资源错配，确保核心战略项目获得充足兵力。
- **关键指标**: 人力投入热力图、核心业务投入占比。

### 1.2 效能对标 (Dept Benchmarking)
- **战略拷问**: 谁是我们的领头羊？谁在拖后腿？
- **核心价值**: 通过横向赛马打破“效能黑盒”，树立改进标杆，识别帮扶对象。
- **关键指标**: 部门 DORA 速度榜 & 质量榜。

### 1.3 资产治理 (Asset Governance)
- **战略拷问**: 我们有多少“僵尸资产”在空耗成本？
- **核心价值**: 降本增效，清理无效库存，降低系统熵增和维护噪音。
- **关键指标**: 僵尸项目数 (Zombie Projects)、闲置存储空间。

### 1.4 全景驾驶舱 (Project Panorama)
- **战略拷问**: 我们的项目健康状况是否具备“上帝视角”？
- **核心价值**: 打破“工程-需求-质量-成本”的数据孤岛，提供一站式体检报告。
- **关键指标**: 项目全景健康度 (Health Score)、进度偏差。

### 1.5 战略组合 (Strategic Portfolio)
- **战略拷问**: 我们的投资组合是否健康？(明星 vs 垃圾)
- **核心价值**: 基于 **DevOps 波士顿矩阵** 进行投资决策。识别高价值高风险项目（重点治理），以及低价值高风险项目（立即止损）。
- **关键指标**: 价值-风险四象限分布 (Value-Risk Quadrant)。

### 1.6 风险治理 (Risk Governance)
- **战略拷问**: 我们的底线是否被突破？谁在“裸奔”？
- **核心价值**: 将“合规性”量化。监控绕过流程发布和高危漏洞积压，守住安全红线。
- **关键指标**: 绕过流程发布率 (Bypass Rate)、安全债务 (Security Debt)。

### 1.7 创新与技术 (Innovation & Tech)
- **战略拷问**: 我们是在重复造轮子，还是在通过“跨界融合”创造复利？
- **核心价值**: 衡量 **组织边界的打破** 和 **技术资产的复利利用**。
- **关键指标**: 跨界创新指数 (Cross-Pollination)、组件复用热力图 (Component Reuse Heatmap)。

### 1.8 内源生态健康度 (InnerSource Ecosystem Health)
- **战略拷问**: 我们是拥有一个充满活力的技术共享社区，还是在一个个技术孤岛中工作？
- **核心价值**: 量化**技术影响力的传递路径**。识别各部门在技术生态中的生态位（供应者 vs 消费者），推动技术复用与共创文化。
- **关键指标**: 内源共创指数 (InnerSource Impact)、跨部门复用强度。
- **计算逻辑**: `InnerSource Index = (跨部门提交的 MR 数 / 总 MR 数) * 0.4 + (被外部引用的组件数 / 总组件数) * 0.6`。

### 1.9 客户体验与隐性满意度 (Shadow Satisfaction)
- **战略拷问**: 我们的交付让业务方感到“爽”吗？
- **核心价值**: 关注交付体验与售后服务，量化“隐性满意度”。识别那些“交付了但口碑极差”的项目。
- **关键指标**: 隐性满意度指数 (Shadow Satisfaction Index - SSI)。
- **计算逻辑**: `SSI = 100 - (SLA惩罚) - (争议惩罚) - (返工惩罚)`。

### 1.10 架构脆性与风险 (Architectural Brittleness)
- **战略拷问**: 我们的底层核心模块是坚固的基石，还是随时会崩塌的纸牌屋？
- **核心价值**: 识别**高风险技术中枢**。防止核心组件在“高复杂度、高变更、低测试覆盖”的情况下由于过度依赖而引发组织级技术塌陷。
- **关键指标**: 架构脆性指数 (Architectural Brittleness Index - ABI)。

### 1.11 计划确定性 (Planning Certainty)
- **战略拷问**: 我们的团队是能够“使命必达”，还是习惯性“画饼”或“延期”？
- **核心价值**: 衡量组织的**确定性交付能力**。识别那些预估精准、节奏平稳的标杆团队。
- **关键指标**: 计划确定性指数 (Planning Certainty Index - PCI)、估算准确度、延期稳定性。

### 1.12 投入产出 (ROI Efficiency)
- **战略拷问**: 我们的每一分钱投入，换回了多少产出？
- **核心价值**: 直接回应 **“钱花得值不值”**。量化人均产能与单需求成本。
- **关键指标**: 人均吞吐量 (Throughput per FTE)、单需求成本 (Cost per Issue)。

### 1.13 协作熵与管理健康 (Team Health & Entropy)
- **战略拷问**: 我们的团队是在高效沟通，还是在无休止的争吵或“一言堂”中内耗？
- **核心价值**: 识别团队的协作模式风险。防止技术独裁（评审民主度低）或沟通冗余（协作熵过高）。
- **关键指标**: 评审民主度 (Review Democracy)、协作熵 (Collab Entropy)、评审乒乓指数。

### 1.14 “胶水人”与隐性贡献 (Glue Person & Implicit Contribution)
- **战略拷问**: 谁在默默为团队“打补丁”，确保项目不掉链子？
- **核心价值**: 识别那些在代码产出之外，通过**知识沉淀、流程守护和争议解决**维持团队高效运作的“灵魂人物”，防止其价值被传统指标掩盖。
- **关键指标**: “胶水人”贡献指数 (Glue-Person Index - GPI)。

- **关键指标**: 供应链流转指数 (SSCV)、构建发布比、跨环境停留时长。

### 1.16 组织依赖透明度 (Organization Dependency Transparency)
- **战略拷问**: 组织的部门墙是否正在拖慢我们的速度？跨部门的阻塞是否会引发系统性的延期“雪球”？
- **核心价值**: 识别**跨边界协作瓶颈**。通过量化跨部门的阻塞链路，识别那些处于“复杂依赖网核心”的脆弱部门，为组织架构优化提供数据支撑。
- **关键指标**: 脆弱性指数 (Vulnerability Index)、跨部门阻塞率、影响因子。

---

## 2. BI 数据宽表设计 (SQL)

以下 SQL 脚本面向高层管理看板，建议以 **月度/季度** 粒度进行汇报。

### 2.1 战略资源投入热力图 (Resource Allocation Heatmap)

- **作用**: 透视企业内部人力资源的真实流向，回答“谁在做什么”的问题。
- **核心价值**: 识别**资源错配**风险（如核心业务投入不足，边缘系统维护成本过高），为 Headcount 调整提供数据依据。
- **核心逻辑**: 
    1. 以 `gitlab_groups` (ROOT层级) 作为业务线划分依据。
    2. 聚合 `commits` 数据，统计过去 90 天内各项目的活跃贡献者和提交量。
    3. 计算每个项目在所属业务线内的资源占比。
- **度量指标**: 
    - **资源集中度 (Resource Share %)**: `项目提交量 / 业务线总提交量`。
    - **项目分级 (Project Tier)**: 基于投入占比自动划分为 `Strategic` (核心), `Active`, `Maintenance` (边缘)。
- **SQL视图**: `view_pmo_resource_heatmap` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**: 
    - **数据源**: 聚合 `projects` (工时/元数据) 和 `commits` (活跃度)。
    - **逻辑**: 按 `root_group` (业务线) 分组，计算每个项目在业务线内的 **提交量占比**。
    - **分级算法**: `>20%` 只有核心项目，`<10次提交` 为边缘项目。


### 2.2 部门效能赛马榜 (Dept DORA Ranking)

- **作用**: 呈现各研发部门的效能水平对比。
- **核心价值**: 通过**横向排名**促进良性竞争，识别卓越团队（作为标杆推广经验）和落后团队（提供资源帮扶）。
- **核心逻辑**: 
    1. 将项目关联到 `organizations` (部门层级)。
    2. 聚合计算 DORA 核心指标：发布频率、变更前置时间、变更失败率。
    3. 使用 `RANK()` 函数生成“速度榜”和“质量榜”。
- **度量指标**: 
    - **发布频率 (Deploy Freq)**: 月均发布次数。
    - **前置时间 (Lead Time)**: 代码合并到发布的平均时长 (小时)。
    - **变更失败率 (Failure Rate)**: 失败部署 / 总部署。
- **SQL视图**: `view_pmo_dept_ranking` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `organizations`, `projects`, `deployments`, `merge_requests`。
    - **逻辑**: 将项目上卷到 `Department` 层级。
    - **核心算法**: 计算月均发布频率、平均 LeadTime、失败率，并使用 `RANK()` 函数分别生成速度榜和质量榜。


### 2.3 僵尸资产治理清单 (Zombie Assets Governance)

- **作用**: 扫描并识别长期闲置的研发资产。
- **核心价值**: **降本增效**。减少存储浪费，降低维护噪音，规避“幽灵代码”带来的安全隐患。
- **核心逻辑**: 筛选出活跃时间在 180 天之前且未被标记为“Archived”的项目。
- **度量指标**: 
    - **闲置天数 (Idle Days)**: 距最后一次活动的天数。
    - **存储占用 (MegaBytes)**: 仓库物理大小。
- **SQL视图**: `view_pmo_zombie_projects` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `projects`。
    - **逻辑**: 筛选 `active_at < 180天` 且 `archived = false` 的项目。
    - **结果**: 按闲置天数倒序，展示项目名称、负责人和存储占用。


### 2.4 项目全景驾驶舱 (Project Comprehensive Cockpit)

- **作用**: 提供单项目的“全科体检报告”，作为数字驾驶舱的底层明细表。
- **核心价值**: 打破数据孤岛，将工程产出、进度管理、质量风险、成本投入**四合一**，为管理层提供上帝视角。
- **核心逻辑**: 
    1. 关联 Gitlab Projects (元数据), Issues (工时+进度), MRs (吞吐), Milestones (计划)。
    2. 关联 SonarQube (质量门禁, Bug, 覆盖率)。
    3. 集成 Tags/Releases (交付版本)。
- **度量指标**: 
    - **进度**: `issue_completion_pct` (需求完成率)。
    - **成本**: `time_variance_hours` (工时偏差：实耗 vs 预估)。
    - **质量**: `quality_gate` (质量门禁状态)。
    - **活跃**: `active_rate_pct` (生命周期活跃率)。
- **SQL视图**: `view_project_overview` (位于 `devops_collector/sql/PROJECT_OVERVIEW.sql`)
- **SQL说明**:
> *注：由于该视图逻辑较为复杂（约 150 行 SQL），请直接参阅独立文件 `PROJECT_OVERVIEW.sql`。*

### 2.5 战略投资组合管理 (Strategic Portfolio Management)

- **作用**: 基于波士顿矩阵模型，对企业所有项目进行战略分类。
- **核心价值**: 辅助高层进行**投资决策**。回答“哪些项目值得追加投入（Stars）”，“哪些项目需要立即止损或还债（Problem Children）”。
- **核心逻辑**: 
    1. **X轴 (Velocity)**: 基于提交量和 MR 量计算对数得分。
    2. **Y轴 (Health)**: 基于 Bug、漏洞和覆盖率计算健康得分。
    3. **分类**: 根据 50/60 分界线自动划分为四个象限。
- **度量指标**: 
    - **交付活跃度 (Velocity Score)**: 0-100分。
    - **质量健康度 (Health Score)**: 0-100分。
    - **创新系数 (Innovation Ratio)**: Feature 工时 / 总工时。
- **SQL视图**: `view_pmo_portfolio_matrix` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `view_project_overview`。
    - **X轴算法**: 对总提交量+合并MR数取对数 `LOG(N+1)`，归一化为 0-100。
    - **Y轴算法**: 基础分 100 分，根据 Bug、漏洞、覆盖率进行阶梯式扣分。
    - **象限划分**: 自动根据 `(50, 60)` 坐标系将项目打上 `Stars/Cows/Dogs/Problem` 标签。


### 2.6 风险治理看板 (Governance Dashboard)

- **作用**: 监控研发流程中的违规行为和安全隐患。
- **核心价值**: 守住研发底线，量化**流程合规性**和**安全债务**。
- **核心逻辑**: 
    1. **流程**: 统计 Commit Title 不包含 'Merge' 关键字且直接推送到主干的比例，识别“绕过 MR”的行为。
    2. **安全**: 统计 SonarQube 中未修复的 `BLOCKER/CRITICAL` 漏洞及其平均积压时长。
- **度量指标**: 
    - **绕过流程发布率 (Bypass Rate)**: 疑似直接 Push 的提交占比。
    - **高危漏洞积压 (Active Blockers)**: 未修复的严重漏洞数。
    - **漏洞平均账龄 (Avg Vuln Age)**: 高危漏洞平均存在天数。
- **SQL视图**: `view_pmo_governance_risk` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `commits`, `sonar_issues`。
    - **流程风险**: 识别 Title 不含 "Merge" 关键字的提交，统计为 Direct Push。
    - **安全风险**: 统计 `BLOCKER/CRITICAL` 级别漏洞的未修复数量和滞留时长。
    - **评级**: 只要有安全债务即为 `Security Risk`，绕过率 > 50% 为 `Process Risk`。


### 2.7 创新与技术资产看板 (Innovation & Tech Assets Dashboard)

- **作用**: 量化组织的技术活力与资产沉淀能力（CTO 视角）。
- **核心价值**: 推动 **InnerSource（内源共建）** 文化，避免“重复造轮子”，识别具有技术领导力（Thought Leadership）的团队。
- **核心逻辑**: 
    1. **跨界 (Cross-Pollination)**: 识别 MR 发起人部门与项目所属部门不一致的贡献，视为“跨团队协作”或“去中心化创新”。
    2. **复用 (Reuse)**: 统计 Star > 5 或 Fork > 2 的项目比例，视为“企业级公共资产”。
- **度量指标**: 
    - **跨界创新指数 (Cross-Pollination Index)**: `非本部门发起的MR数 / 总MR数`。
    - **资产复用率 (Asset Reuse Rate)**: 高价值项目(High Star/Fork)占比。
- **SQL视图**: `view_pmo_innovation_metrics` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `merge_requests` (关联 users), `projects` (stars/forks)。
    - **创新指数**: 筛选 MR 作者部门 != 项目所属部门的记录，视为跨界。
    - **资产价值**: 筛选 Stars >= 5 或 Forks >= 2 的项目，视为高价值公共组件。


### 2.8 组件复用热力图 (Component Reuse Heatmap)

- **作用**: 可视化展示跨部门的技术供应与消费关系。
- **核心价值**: 识别企业的“技术引擎”（核心供应部门）与“复用大户”（高效能消费部门），发现由于缺乏共享而导致的重复造轮子风险。
- **核心逻辑**: 
    1. **归一化映射**: 从 `gitlab_packages` 提取组件供应源，从 `gitlab_dependencies` 提取组件消费端。
    2. **跨域碰撞**: 筛选供应项目所属部门 != 消费项目所属部门的记录。
    3. **热力计算**: 以供应部门为 X 轴，消费部门为 Y 轴，复用项目数为热力强度。
- **度量指标**: 
    - **复用强度 (Reuse Intensity)**: 跨部门引用的项目总数。
    - **供应活跃度**: 产生的公共组件被多少个外部部门使用。
- **SQL视图**: `view_pmo_innersource_reuse_heatmap` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `gitlab_packages`, `gitlab_dependencies`, `organizations`, `projects`。
    - **逻辑**: 使用 `WITH` 子句分别构建供应方清单 and 消费方清单，基于包名连接并过滤同部门引用。
    - **可视化建议**: 推荐使用 ECharts 热力图，X轴为 Provider Dept，Y轴为 Consumer Dept。


### 2.9 客户满意度洞察与 SSI (Shadow Satisfaction Insights)

- **作用**: 在缺乏问卷系统的情况下，基于协作数据推导“隐性满意度 (Shadow Satisfaction Index)”。
- **核心价值**: **工程行为映射体验**。识别“低响应、高争议、多返工”的风险交付。
- **核心逻辑**: 
    1. **响应性 (SLA)**: 以 Bug MTTR 为基准。每超过 24h 扣 10 分（上限 40）。公式：$Penalty_{SLA} = (MTTR / 24) * 10$。
    2. **争议度 (Controversy)**: 统计评论数 > 10 的 Issue 占比。反映方案冲突，扣分权重 1.5（上限 30）。
    3. **返工率 (Rework)**: 统计 Reopened 的任务占比。反映交付质量，扣分权重 3.0（上限 30）。
- **度量指标**: 
    - **SSI 指数**: 0-100 分综合得分。
    - **满意度评级**: 80+(Health), 60-80(Warning), <60(Risk)。
- **SQL视图**: `view_pmo_customer_satisfaction` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)

### 2.10 评审民主度与协作熵 (Review Democracy & Entropy)

- **作用**: 识别“形式主义评审”、技术垄断及沟通效能瓶颈。
- **核心价值**: 确保代码评审的**真实有效性**与**决策去中心化**。
- **核心逻辑**: 
    1. **评审民主度 (Review Democracy)**: 统计 MR 独立评审人数量。若 `avg_reviewers` 长期处于低位，暗示代码合并权过度集中。
    2. **协作熵 (Collab Entropy)**: 计算 MR 平均人工备注（Comment）数。代表单次变更触发的探讨密度。
    3. **评审乒乓 (Ping-Pong Index)**: 统计 MR 状态打回 (Reopened) 的平均轮次。过高 ( > 4) 代表协作低效。
- **SQL视图**: `view_team_review_quality_entropy` (位于 `devops_collector/sql/TEAM_ANALYTICS.sql`)


### 2.11 架构脆性指数 (Architectural Brittleness Index)

- **作用**: 识别研发资产中因“高耦合+高变动+低质量”构成的技术黑洞。
- **核心价值**: **预防系统性崩溃**。指导 CTO 在何处投入重构资源。
- **核心逻辑**: 
    1. **依赖影响力 (In-Degree)**: 统计外部项目对该项目产定制品的引用数。
    2. **代码流转率 (Churn)**: 统计过去 90 天的提交频次，反映模块活跃度。
    3. **技术硬伤 (Risk)**: 提取 SonarQube 的圈复杂度与单测覆盖率。
- **计算公式**: $ABI = log_2(InDegree+1)*20 + \frac{Complexity}{10} + (100 - Coverage) + log_2(Churn+1)*10$
- **度量指标**: 
    - **ABI 分值**: 0-150分。
    - **状态判定**: `Brittle Core` (高影响力且高分), `Stable Engine` (高影响力但低分)。
- **SQL视图**: `view_pmo_architectural_brittleness` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)


### 2.13 计划确定性模型 (Planning Certainty Model)

- **作用**: 量化团队的承诺履行能力与估算水准。
- **核心价值**: **透明化交付灰盒**。识别过度乐观的估算陷阱，提升业务排期的可预测性。
- **核心逻辑**: 
    1. **估算偏差 (Estimation Variance)**: 统计 `Spent Hours` 与 `Original Estimate` 的偏差率。
    2. **延期惯性 (Delay Inertia)**: 统计 Issue 变更 history 中 `due_date` 被延后的频率。
    3. **完成质量 (Completion Quality)**: 结合是否在迭代内完成。
- **计算公式**: $PCI = (Accuracy \times 0.7) + (\frac{1}{DelayCount+1} \times 0.3) \times 100$
- **度量指标**: 
    - **PCI 分值**: 0-100分。
    - **状态判定**: `High Reliability`, `Moderate`, `Low Reliability`.
- **SQL视图**: `view_pmo_planning_certainty` (位于 `devops_collector/sql/TRADITIONAL_PM_ANALYTICS.sql`)


### 2.14 投入产出效能仪表盘 (ROI & Efficiency Dashboard)

- **作用**: 回答 CTO/CEO 关于“钱花得值不值”的拷问，量化工程团队的生产力与成本结构。
- **核心价值**: **效能黑盒透明化**。通过 Input/Output 比率识别低效团队（成本高产出低）和高效能标杆。
- **核心逻辑**: 
    1. **Input**: 聚合活跃贡献者人数 (FTE Proxy) 和实际消耗工时 (Spent Hours)。
    2. **Output**: 聚合已合并的 MR (技术产出) 和已关闭的 Issue (业务产出)。
    3. **Efficiency**: 计算两者比率。
- **度量指标**: 
    - **人均吞吐量 (Throughput per FTE)**: `Merged MRs / Active Contributors`。衡量单兵作战能力。
    - **单需求成本 (Cost per Issue)**: `Spent Hours / Closed Issues`。衡量业务交付的“昂贵程度”。
    - **工时转化率 (Planning Accuracy)**: `Extimated / Spent`。衡量计划准确性。
- **SQL视图**: `view_pmo_roi_efficiency` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `view_project_overview`。
    - **Input**: 汇总 `active_contributors` 和 `spent_hours`。
    - **Output**: 汇总 `merged_mrs` 和 `closed_issues`。
    - **Metrics**: 计算投入产出比 `Throughput / FTE` 和 `Hours / Issue`。


### 2.15 "胶水人"贡献模型 (The Glue-Person Index - GPI)

- **作用**: 识别通过非代码产出维持团队高效运作的"灵魂人物"。
- **核心价值**: **完善人才评价体系**。奖励那些让别人更高效的开发者，防止其价值被传统指标掩盖。
- **核心逻辑**: 
    1. **知识布道 (Wiki Score)**: 统计 90 天内在 `gitlab_wiki_logs` 中的创建与更新动作。识别主动沉淀知识、编写文档的"布道者"。
    2. **流程守护 (Process Score)**: 统计对 `gitlab_issue_events` 中标签 (Labels)、里程碑 (Milestones) 的维护频次，以及对 Jira `due_date` 的调整动作。识别主动优化流程、确保项目合规的"守护者"。
    3. **协作催化 (Help Score)**: 统计在 `notes` 表中的人工评论活跃度（排除系统消息）。识别积极响应、解决争议、解除他人阻塞的"催化剂"。
- **计算公式**: $GPI = (WikiScore \times 5) + (ProcessScore \times 2) + (HelpScore \times 0.5)$
    - **权重说明**: Wiki 贡献权重最高（5倍），因为知识沉淀具有长期复利效应；流程守护次之（2倍），因为它直接影响团队效率；评论帮助权重最低（0.5倍），因为它是日常协作的基础行为。
- **度量指标**: 
    - **GPI 分值**: 0-200+分。
    - **角色定性**: 
        - `Team Catalyst (金牌催化剂)` (>100): 组织内极具影响力的隐性导师。
        - `Bridge Builder (协作桥梁)` (50-100): 擅长跨团队沟通与流程梳理。
        - `Supportive Member (支持型成员)` (20-50): 积极参与协作，提供帮助。
        - `Silent Contributor (默默贡献者)` (<20): 扎实履行岗位职责。
- **SQL视图**: `view_hr_glue_person_index` (位于 `devops_collector/sql/HR_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `gitlab_wiki_logs`, `gitlab_issue_events`, `jira_issue_histories`, `notes`, `users`。
    - **Wiki 统计**: 汇总 90 天内的 Wiki 创建、更新动作。
    - **流程统计**: 合并 GitLab Issue Events (label/milestone) 和 Jira History (status/labels/duedate) 的元数据修正动作。
    - **帮助统计**: 统计非系统消息的评论总数。
    - **角色判定**: 根据加权总分自动分配角色标签。


### 2.16 软件供应链流转效率 (Software Supply Chain Velocity - SSCV)

- **作用**: 识别交付全链路中的"物理淤积点"，量化从代码合并到生产发布的流转效率。
- **核心价值**: **推动持续交付 (CD) 深度落地**。识别环境间的等待与阻塞，优化发布流水线，实现"制品即发布"的极致体验。
- **核心逻辑**: 
    1. **构建活跃度 (Build Ops)**: 统计 `pipelines` 表中过去 90 天的总构建次数与成功构建次数。
    2. **交付漏斗 (Pipeline Pass Rate)**: 计算 `成功构建数 / 总构建数`，识别"试错型"项目（构建成功率低，反复重试）。
    3. **环境流转时延 (Env Dwell Time)**: 通过 `deployments` 表，关联 Staging 与 Production 环境的 `ref` (branch/tag)，计算同一制品在两个环境间的时间差。这反映了制品在 Staging 环境的"停留时长"。
    4. **构建发布比 (Build per Release)**: 计算 `总构建次数 / 生产发布次数`，识别构建浪费（如每次发布需要 15+ 次构建，说明流程不稳定）。
- **计算公式**: 
    - $DwellTime = AVG(Production.created\_at - Staging.created\_at)$ (单位: 小时)
    - $BuildPerRelease = TotalBuilds / ProdDeployCount$
    - $PassRate = SuccessfulBuilds / TotalBuilds \times 100\%$
- **度量指标**: 
    - **avg_env_dwell_hours**: 跨环境平均停留时长。
    - **build_per_release**: 每次发布所需的平均构建次数。
    - **pipeline_pass_rate**: 构建成功率 (%)。
    - **supply_chain_status**: 
        - `SMOOTH: DevOps Pipeline` (顺畅): 环境流转快速，构建成功率高。
        - `CLOGGED: Deployment Bottleneck` (淤积): 环境停留时长 >72h，说明 Staging 到 Production 的发布流程存在人工审批或环境锁定问题。
        - `INEFFICIENT: Try-and-Error` (试错型): 构建发布比 >15，说明 CI/CD 流程不稳定，需要优化测试策略。
        - `INACTIVE`: 无生产发布记录。
- **SQL视图**: `view_pmo_software_supply_chain_velocity` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `pipelines`, `deployments`, `projects`, `gitlab_groups`。
    - **构建统计**: 汇总 90 天内的构建总数与成功数。
    - **环境匹配**: 通过 `ref` 字段关联同一制品在不同环境的部署记录。假设 Staging 部署先于 Production 部署。
    - **时延计算**: 提取 Staging 到 Production 的时间差平均值。
    - **状态判定**: 根据时延和构建比自动分类供应链状态。

### 2.17 组织依赖透明度 (Organization Dependency Transparency - ODT)

- **作用**: 识别跨部门的协作阻塞节点，量化"部门墙"的负面影响。
- **核心价值**: **为组织架构优化提供数据支撑**。预判延期雪球效应。
- **核心逻辑**: 
    1. **实体映射**: 建立 Jira Issue 与 GitLab 部门的关联链路。
    2. **依赖抓取**: 从 `traceability_links` 中提取 `blocks` 的跨部门阻塞关系。
    3. **脆弱性量化**: 统计各部门受外部影响的任务比例。
- **计算公式**: $VulnerabilityIndex = log_2(BlockedTaskCount + 1) \times 20$
- **度量指标**: 
    - **external_blocker_dept_count**: 有多少个外部部门在阻塞我。
    - **vulnerability_index**: 脆弱性指数 (0-100+分)。
    - **dependency_status**: `CRITICAL` (≥3个外部部门), `HIGH` (>5个阻塞任务), `STABLE`。
- **SQL视图**: `view_pmo_org_dependency_transparency` (位于 `devops_collector/sql/TRADITIONAL_PM_ANALYTICS.sql`)

---

## 3. 现有 SQL 资产复用建议

PMO 视角的分析高度依赖数据的**聚合 (Aggregation)** 和 **关联 (Join)**。建议复用以下基础视图：

1.  **`dept_performance.sql`**: 提供了很好的部门级容量和基础 DORA 数据，是 `view_pmo_dept_ranking` 的数据源基础。
2.  **`process_deviation.sql`**: 如果发现某部门的“游离代码率”异常高，PMO 应介入审计其合规性。
3.  **`HR_ANALYTICS.sql` 中的 `view_hr_user_tech_stack`**: 可以上卷到部门层级，生成“部门技术栈大图”，辅助技术战略选型（例如：我们部门是不是 Python 太多了，Java 太少了？）。

---

## 4. 战略价值总结 (Strategic Conclusion)

**DevInsight PMO 解决方案** 不再局限于“看代码写了多少行”的初级阶段，而是构建了一套完整的 **数字化研发管理与决策系统**。

1.  **从“盲人摸象”到“全景上帝视角”**：
    通过 `Project Overview` 和 `Resource Heatmap`，PMO 第一次拥有了完整的战场态势图，不再依赖主观汇报。

2.  **从“事后救火”到“事前风控”**：
    通过 `Portfolio Matrix` 和 `Risk Governance`，CTO 可以提前识别出那些“高活跃度但质量崩坏”的第四象限项目，将技术债务危机消灭在萌芽状态。这通常是 CTO 最睡不着觉的地方，现在有了从容应对的数据支撑。

3.  **从“重复造轮子”到“技术复利”**：
    通过 `Innovation` 和 `Tech Assets` 指标，我们鼓励跨界融合，奖励资产沉淀，推动组织从“人力堆砌型”向“资产复用型”进化。

4.  **从“成本中心”到“价值中心”**：
    通过 `ROI Efficiency` 和 `Customer Satisfaction`，我们用 CFO 听得懂的语言（投入产出比）和业务方在乎的指标（满意度），证明了技术团队的商业价值。

这不仅是一套报表，更是 **组织进化的罗盘**。它指引着整个研发组织在 **“做正确的事 (Strategic)”** 与 **“正确地做事 (Tactical)”** 之间找到最佳平衡，实现可持续的高质量增长。

---

## 5. 补充：传统项目管理与项目群管理指标 (Expanded Metrics)

为了进一步完善 PMO 的治理体系，我们引入了以下基于传统 PMBOK 维度和项目群/组合管理维度的核心指标。

### 5.1 传统项目管理维度 (Traditional Project Management)

这些指标侧重于单项目的交付确定性，即“铁三角”（进度、成本、质量）的闭环管理。

| 维度 | 度量指标 (Metrics) | 说明 (Definition) | 管理意义 (Strategic Value) |
| :--- | :--- | :--- | :--- |
| **进度** | **进度偏差 (SV)** | `实际/预测完成时间 vs 计划完成时间` | 评估项目是否延期，识别关键路径瓶颈。 |
| **进度** | **里程碑达成率** | `已按时达成的里程碑数 / 总里程碑计划数` | 衡量阶段性目标交付的确定性。 |
| **范围** | **需求变更频率** | `周期内发生变更的需求数 / 需求总数` | 识别需求不稳定性，防范范围蔓延风险。 |
| **成本/工时** | **工时偏差 (TV)** | `实际消耗工时 vs 原始预算/估算工时` | 评估估算准确度及人力成本超预算风险。 |
| **成本/工时** | **工时转化率** | `Spent / Estimated` | 衡量计划与实际的对齐程度。 |
| **质量** | **缺陷逃逸率** | `上线后发现的缺陷数 / 总缺陷数` | 评估测试环节的有效性和线上发布质量。 |
| **风险** | **风险暴露指数** | `未关闭的高危风险数 * 风险存续时长` | 量化单项目的风险积压压力。 |

### 5.2 项目群与项目组合管理维度 (Program & Portfolio)

这些指标侧重于跨项目的资源平衡、战略一致性和投资组合的整体健康。

| 维度 | 度量指标 (Metrics) | 说明 (Definition) | 管理意义 (Strategic Value) |
| :--- | :--- | :--- | :--- |
| **战略一致性** | **战略对齐度得分** | `符合战略支柱分类的项目数 / 总项目数` | 确保组织资源正投入到最关键的业务方向。 |
| **资源效率** | **多项目资源冲突率** | `被标记为 Overbooked 的核心人力百分比` | 识别关键资源（如架构师、核心开发）的瓶颈。 |
| **生命周期** | **组合健康度分布** | `基于 Health Score 的项目等级分布 (红/黄/绿)` | 提供整体组合的稳健性评估。 |
| **投资回报** | **组合 ROI 效率** | `组合总交付价值 (Business Value) / 组合总投入` | 评估项目群作为一个整体的经济效益。 |
| **协同依赖** | **跨项目阻塞率** | `被外部项目 Block 的任务数 / 总任务数` | 识别组织内部的协同阻塞节点和系统性依赖风险。 |

---

## 6. 指标落地数据源映射 (Jira Data Mapping)

为了支撑上述指标，我们需要扩展 Jira 数据采集能力：
- **里程碑**: 映射自 Jira 的 `fixVersions`。
- **预算工时**: 映射自 Jira 的 `timeoriginalestimate`。
- **进度/工时**: 映射自 Jira 的 `timespent` 和 `timeestimate`。
- **依赖关系**: 映射自 Jira 的 `issuelinks`，存储于 `traceability_links` 表。
- **风险/变更**: 通过自定义标签 (`labels`) 或特定 Issue Type (如 `Risk`, `Change Request`) 进行自动识别。
- **战略分类**: 基于 Jira Project 属性或特定的全局层级标签。

---

## 7. 财务投入透明化 (Financial Transparency)

为了实现“分摊到位的数字化财务管理”，系统通过结合工程工时的产出与人力单价的投入，构建了自动化的成本核算模型。

### 7.1 人力成本核算模型 (Labor Cost Model)

**核算公式**:
`项目/任务成本 = (实际消耗工时 / 3600) * 岗位标准时薪`

**数据链路**:
1.  **投入端 (Input)**: 从 Jira `jira_issues` 采集 `time_spent`（实际消耗工时，秒）。
2.  **单价端 (Rate)**: 基于 `users.job_title_level`（职级）在 `labor_rate_configs` 表中查找对应的 `hourly_rate`（标准时薪）。
3.  **归一化 (Normalization)**: 系统自动将不同系统的账号对齐到全局 User，确保工时能够精准挂接到人员及其单位成本。

### 7.2 财务分析维度

| 分析维度 | 指标 (Metrics) | 说明 (Definition) | 价值 |
| :--- | :--- | :--- | :--- |
| **项目成本** | **累计人力投入成本** | 关联所有 Issue 的工时成本总和 | 实时掌握项目资金消耗情况 (Burn Rate)。 |
| **部门损益** | **部门月度研发支出** | 部门内所有成员月度产生的工时成本 | 作为研发中心向财务汇报的自动化依据。 |
| **ROI 评估** | **单产出价值比 (Cost/Value)** | `项目总成本 / 已交付需求量` | 识别交付最“昂贵”的项目，优化资源配置。 |
| **预算预警** | **预算消耗率** | `已发生人力成本 / 项目原始预算` | 提前预判预算超支风险。 |

### 7.3 落地建议 (SQL View)
使用 `view_pmo_project_labor_costs` 视图进行实时核算（详见 `TRADITIONAL_PM_ANALYTICS.sql`）。

---

## 8. 多项目风险预警引擎 (Risk Warning Engine)

预警引擎旨在将“被动查看报表”转变为“主动推送风险”，通过企业微信 (WeCom) 即时触达项目负责人与 PMO。

### 8.1 预警触发规则 (Risk Rules)

| 风险类别 | 触发阈值 (Anomalies) | 严重等级 | 推送建议 |
| :--- | :--- | :--- | :--- |
| **进度风险** | `view_jira_iron_triangle.completion_rate_pct < 进度时间轴比例 - 15%` | 高 (High) | 即时推送项目经理 |
| **成本风控** | `view_jira_iron_triangle.effort_variance_pct > 20%` (超支) | 中 (Mid) | 每周汇总推送 PMO |
| **质量红线** | `view_project_overview.quality_gate = 'ERROR'` | 高 (High) | 即时推送 Tech Lead |
| **安全债务** | `view_pmo_governance_risk.avg_vuln_age_days > 7` | 中 (Mid) | 隔日提醒负责人 |
| **协作瓶颈** | `view_jira_dependency_analysis.risk_level = 'CRITICAL_BLOCK'` | 高 (High) | 即时推送阻塞方与被阻塞方 |

### 8.2 推送机制 (Notification Mechanism)

*   **通道**: 企业微信机器人 Webhook。
*   **格式**: Markdown 卡片，包含：
    *   **风险标题**: 简洁明了（如：[进度预警] 某支付系统延期风险）。
    *   **异常详情**: 具体的度量值对比（如：当前完成度 30%，预期完成度 55%）。
    *   **责任人**: @ 对应的负责人账号。
    *   **处理建议**: 自动化生成初步行动项。

### 8.3 落地建议 (Automation)
1.  **SQL 支撑**: 创建 `view_pmo_risk_anomalies` 汇总所有风险。
2.  **Python 引擎**: 编写 `scripts/wecom_risk_bot.py` 定时运行，识别异常并调用 Webhook。


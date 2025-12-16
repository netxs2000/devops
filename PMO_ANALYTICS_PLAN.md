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
- **关键指标**: 跨界创新指数 (Cross-Pollination)、资产复用率。

### 1.8 客户体验 (Customer Satisfaction)
- **战略拷问**: 我们的交付让业务方感到“爽”吗？
- **核心价值**: 关注交付体验与售后服务，量化“隐性满意度”。
- **关键指标**: Bug响应速度 (SLA)、需求争议度 (Controversy Rate)。

### 1.9 投入产出 (ROI Efficiency)
- **战略拷问**: 我们的每一分钱投入，换回了多少产出？
- **核心价值**: 直接回应 **“钱花得值不值”**。量化人均产能与单需求成本。
- **关键指标**: 人均吞吐量 (Throughput per FTE)、单需求成本 (Cost per Issue)。

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


### 2.8 客户满意度洞察 (Customer Satisfaction Insights)

- **作用**: 在缺乏问卷系统的情况下，基于协作数据推导“影子满意度”。
- **核心价值**: 关注**交付体验**。不仅仅是看“做完了没有”，还要看“做得开不开心（争议度）”和“售后好不好（已读回不回）”。
- **核心逻辑**: 
    1. **响应速度 (SLA)**: 计算 Bug 的平均修复时长 (MTTR)，响应越快满意度越高。
    2. **争议度 (Controversy)**: 统计评论数异常高 (>10条) 的 Issue 比例，反映需求沟通是否顺畅。
    3. **返工率 (Rework)**: 统计被打回 (Reopened) 的需求比例。
- **度量指标**: 
    - **Bug平均修复时长 (Bug MTTR)**: 小时。
    - **高争议需求占比 (High Controversy %)**: 评论>10的Issue占比。
    - **满意度预警**: 综合上述指标给出的红绿灯状态。
- **SQL视图**: `view_pmo_customer_satisfaction` (位于 `devops_collector/sql/PMO_ANALYTICS.sql`)
- **SQL说明**:
    - **数据源**: `issues`。
    - **MTTR**: 计算关闭状态的 Bug 的平均修复时长 (ClosedAt - CreatedAt)。
    - **争议度**: 筛选 `user_notes_count > 10` 的 Issue 比例。
    - **综合预警**: 如果 MTTR > 72小时或争议度 > 20%，判定为 Low Satisfaction Risk。


### 2.9 投入产出效能仪表盘 (ROI & Efficiency Dashboard)

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

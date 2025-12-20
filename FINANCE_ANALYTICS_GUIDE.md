# 财务视角的研发效能洞察体系

## 概述

本文档详细说明了基于现有元数据构建的六大财务洞察模型，旨在将研发活动转化为 CFO 和财务部门能够理解的财务语言。

---

## 1. 项目真实盈利能力分析 (Project True Profitability Analysis)

### 核心问题
这个项目到底赚钱还是亏钱？

### 数据链路
- **收入端**: `revenue_contracts` → `contract_payment_nodes` (已达成的收款节点)
- **成本端**: 
  - 人力成本: `jira_issues.time_spent` × `labor_rate_configs.hourly_rate`
  - 云成本: `purchase_contracts` (按项目分摊)
  - 外包成本: `purchase_contracts` (外包供应商)

### 核心指标
- **毛利率 (Gross Margin)**: `(总收入 - 总成本) / 总收入 × 100%`
- **人效比 (Revenue per FTE)**: `总收入 / 活跃人数`
- **成本结构**: 人力成本占比 vs 外包成本占比 vs 云成本占比

### 管理价值
- ✅ 识别"伪需求"项目（高投入低回报）
- ✅ 为定价策略提供成本基准
- ✅ 优化资源配置（将人力从亏损项目转移到盈利项目）

### SQL 视图
`view_finance_project_profitability` (位于 `devops_collector/sql/FINANCE_ANALYTICS.sql`)

---

## 2. 里程碑交付与回款健康度 (Milestone-Payment Health)

### 核心问题
技术交付进度是否与财务回款节奏同步？

### 数据链路
- `contract_payment_nodes.linked_milestone_id` → `milestones.state`
- `milestones.due_date` vs `contract_payment_nodes.achieved_at`

### 核心指标
- **交付-回款延迟 (Delivery-Payment Lag)**: 里程碑完成时间 - 预期回款时间
- **回款风险指数**: 已逾期但未完成的里程碑数量
- **现金流预测准确度**: 实际回款时间 vs 计划回款时间的偏差

### 管理价值
- ✅ 预警现金流断裂风险
- ✅ 识别"技术交付快但商务回款慢"的异常项目
- ✅ 为财务部门提供精准的现金流预测

### SQL 视图
`view_finance_milestone_payment_health` (位于 `devops_collector/sql/FINANCE_ANALYTICS.sql`)

---

## 3. 人力成本燃烧率与预算预警 (Burn Rate & Budget Alert)

### 核心问题
项目的人力预算还能撑多久？

### 数据链路
- **实际消耗**: `jira_issues.time_spent` × `labor_rate_configs.hourly_rate`
- **预算基准**: `revenue_contracts.total_value` × 预设成本率（如 70%）

### 核心指标
- **燃烧率 (Burn Rate)**: 月均人力成本消耗速度
- **预算消耗率**: `已发生成本 / 总预算 × 100%`
- **跑道时长 (Runway)**: `剩余预算 / 月均燃烧率` (单位: 月)

### 管理价值
- ✅ 提前 2-3 个月预警预算超支
- ✅ 识别"低产出高消耗"的项目
- ✅ 为项目经理提供成本控制依据

### SQL 视图
`view_finance_burn_rate_alert` (位于 `devops_collector/sql/FINANCE_ANALYTICS.sql`)

---

## 4. 技术债务的财务量化 (Technical Debt Financial Impact)

### 核心问题
技术债务到底"值多少钱"？

### 数据链路
- **债务工时**: `sonar_issues.sqale_index` (技术债务修复工时，单位: 分钟)
- **人力单价**: `labor_rate_configs.hourly_rate`
- **债务成本**: `(sqale_index / 60) × hourly_rate`

### 核心指标
- **债务总额 (Total Debt Cost)**: 所有未修复技术债务的人力成本总和
- **债务密度 (Debt Density)**: `债务成本 / 代码行数 (KLOC)`
- **债务利息 (Debt Interest)**: 因技术债务导致的额外返工成本

### 管理价值
- ✅ 用 CFO 听得懂的语言（金额）量化技术债务
- ✅ 为重构项目争取预算提供数据支撑
- ✅ 识别"债务黑洞"项目

### SQL 视图
`view_finance_tech_debt_cost` (位于 `devops_collector/sql/FINANCE_ANALYTICS.sql`)

---

## 5. 外包 vs 自研的成本效益分析 (Outsourcing vs In-house Cost-Benefit)

### 核心问题
外包真的比自研便宜吗？

### 数据链路
- **外包成本**: `purchase_contracts` (vendor_name 包含"外包"关键字)
- **自研成本**: 内部团队的 `time_spent × hourly_rate`
- **质量对比**: 外包项目 vs 自研项目的 Bug 密度、返工率

### 核心指标
- **单位产出成本 (Cost per Output)**: `总成本 / 已交付功能点数`
- **质量调整成本 (Quality-Adjusted Cost)**: `总成本 × (1 + 返工率)`
- **外包溢价率**: `(外包单价 - 自研单价) / 自研单价 × 100%`

### 管理价值
- ✅ 为"外包 vs 自研"决策提供量化依据
- ✅ 识别"看起来便宜，实际很贵"的外包陷阱
- ✅ 优化供应商选择策略

### SQL 视图
`view_finance_outsourcing_analysis` (位于 `devops_collector/sql/FINANCE_ANALYTICS.sql`)

---

## 6. 研发资本化合规性监控 (R&D Capitalization Compliance)

### 核心问题
哪些研发投入可以资本化？是否符合会计准则？

### 数据链路
- **工时分类**: `jira_issues.labels` (包含 "Feature" 的为资本化，"Bug/Refactor" 为费用化)
- **成本归集**: `cost_codes.default_capex_opex`
- **合规校验**: 资本化工时占比是否在合理范围（如 30%-70%）

### 核心指标
- **资本化率 (Capitalization Rate)**: `资本化工时 / 总工时 × 100%`
- **资本化金额**: `资本化工时 × hourly_rate`
- **合规风险指数**: 偏离行业基准的程度

### 管理价值
- ✅ 降低财务审计风险
- ✅ 优化财务报表（将部分研发成本转为资产）
- ✅ 为税务筹划提供数据支撑

### SQL 视图
`view_finance_capex_compliance` (位于 `devops_collector/sql/FINANCE_ANALYTICS.sql`)

---

## 实施建议

### 数据准备
1. **配置人力费率**: 在 `labor_rate_configs` 表中维护各职级的标准时薪
2. **录入收入合同**: 在 `revenue_contracts` 表中录入商务合同信息
3. **关联里程碑**: 在 `contract_payment_nodes` 表中将回款节点与 GitLab Milestone 关联
4. **标记外包项目**: 在 `purchase_contracts` 表中标注外包供应商

### 使用场景
- **月度财务会议**: 使用 `view_finance_project_profitability` 汇报项目盈利情况
- **现金流预测**: 使用 `view_finance_milestone_payment_health` 预测未来 3-6 个月的回款
- **预算审查**: 使用 `view_finance_burn_rate_alert` 识别预算超支风险
- **年度审计**: 使用 `view_finance_capex_compliance` 提供资本化依据

### 预警阈值建议
- **毛利率**: < 20% 为红线，需要重新评估项目定价或成本控制
- **预算消耗率**: > 90% 触发紧急预警
- **跑道时长**: < 2 个月需要立即申请追加预算
- **资本化率**: 偏离 30%-70% 区间需要财务部门审核

---

## 附录：财务术语对照表

| 财务术语 | 技术实现 | 说明 |
|:---|:---|:---|
| 毛利率 (Gross Margin) | `(Revenue - Cost) / Revenue` | 项目盈利能力的核心指标 |
| 燃烧率 (Burn Rate) | 月均人力成本 | 创业公司常用的现金流指标 |
| 跑道 (Runway) | `剩余预算 / 燃烧率` | 预算还能支撑多久 |
| 资本化 (Capitalization) | 将研发支出转为资产 | 影响财务报表和税务 |
| CAPEX | Capital Expenditure | 资本性支出（如新功能开发） |
| OPEX | Operating Expenditure | 运营性支出（如 Bug 修复） |

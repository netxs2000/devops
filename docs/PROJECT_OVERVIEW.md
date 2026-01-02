# 项目全景概览 (Project Comprehensive Overview)

## 1. 概述 (Overview)

**项目全景概览** 是一套基于 GitLab、SonarQube、Jenkins、Jira、ZenTao、JFrog/Nexus 以及成本财务数据的综合分析体系。它打破了单一工具的数据孤岛，利用 **Dagster** 进行全链路任务编排，并通过 **dbt** 实现模型化数据转换，将离散的工程产出、质量红线、资源投入与 ROI 融合为一张“上帝视角”的数据地图。

## 2. 目的与意义 (Purpose & Value)

### 2.1 目的

- **全链路追踪**：实现从“需求入池 -> 代码提交 -> 安全扫描 -> 自动化测试 -> 版本发布 -> 成本分摊”的 360° 可视化。
- **软件定义资产 (SDA)**：通过 Dagster 将每一个指标定义为数据资产，确保血缘清晰、按需更新。
- **自动治理解耦**：利用 Pydantic V2 契约模式，确保前端展示与底层采集引擎的深度解耦。

### 2.2 作用

1. **数字驾驶舱 (Digital Cockpit)**：作为 BI 工具（Streamlit, Superset）的底层数据源，直接展示所有项目的红绿灯状态。
2. **数据质量守卫**：集成 **Great Expectations (GE)**，在资产产出前自动执行断言（非空、范围、引用一致性），确保决策依据的真实性。
3. **治理效率驱动**：通过“流动效能”和“跨项目阻塞”指标，定位组织内的管理瓶颈。

---

## 3. 指标体系详解 (Metrics Dictionary)

本体系目前通过 **dbt models** 维护核心逻辑。

### 3.1 资产交付效能 (Delivery Velocity)

| 指标 | 业务含义 | 计算引擎 |
| :--- | :--- | :--- |
| `dora_deployment_frequency` | 部署频率 | dbt fct_dora_metrics |
| `dora_lead_time_for_changes` | 变更前置时间 | dbt fct_dora_metrics |
| `flow_efficiency` | 流动速率 (排除阻塞时间) | dbt int_issue_status_cycles |

### 3.2 财务与 ROI (FinOps) 🌟

| 字段名 | 业务含义 | 说明 |
| :--- | :--- | :--- |
| `labor_cost_accrual` | 人力成本权责发生额 | 结合 `mdm_calendar` 去除节假日后的精确核算 |
| `capitalization_audit` | 研发资本化审计点 | 区分功能开发 (CAPEX) 与 故障维护 (OPEX) |
| `roi_score` | 研发投入产出比 | `(合同业绩达成 / 累计研发投入成本)` |

### 3.3 安全与合规 (Security & Compliance)

| 指标 | 业务含义 | 数据来源 |
| :--- | :--- | :--- |
| `oss_license_risk` | 开源许可证违规风险 | OWASP Dependency-Check |
| `cve_vulnerability_count` | 组件已知漏洞数 | OWASP Dependency-Check |
| `quality_gate_status` | 质量门禁 (Sonar/Pipeline) | GitLab/SonarQube API |

### 3.4 AI 智能标签 (AI Insights)

| 字段名 | 业务含义 | 说明 |
| :--- | :--- | :--- |
| `ai_risk_level` | MR 风险智能评级 | 基于 AI 对变动行数、业务敏感度的分类 |
| `ai_task_summary` | 任务语义自动摘要 | 利用 LLM 自动修正模糊的需求标题 |

---

## 4. 数据治理架构 (Data Governance)

### 4.1 编排与血缘

- **引擎**: Dagster Daemon
- **元数据**: 自动摄取至 **DataHub**，实现数据字段的全文检索与业务百科。

### 4.2 质检标准 (Data Quality)

系统在 `dagster_repo/assets/check_points` 中定义了以下 GE 校验规则：

- **Schema 强校验**: 每一批采集到的原始 JSON 必须通过 Pydantic 校验。
- **业务逻辑校验**: 例如“结束日期必须晚于开始日期”、“用户 ID 必须在 `mdm_identities` 中存在”。

## 5. 总结

本系统不仅仅是一个报表工具，它是**数字化管理的底座**。通过 Dagster 和 dbt 的引入，我们将原本碎片的脚本转变为可维护、可测试、可治理的数据资产产线。

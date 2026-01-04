# 研发主数据与工程数据仓库架构技术白皮书 (v4.0)

> **核心理念**: 主数据为基，活动流为核，驱动工程效能与研发成本的透明化治理。

---

## 1. 架构愿景与演进

在研发数字化转型过程中，“数据烟囱”和“口径不一”是核心痛点。本架构通过 **MDM (主数据管理)** 与 **dbt 分层建模** 的深度结合，构建了从原子操作到业务洞察的端到端可验证链路。

* **从工具导向转向实体导向**: 不再关注“GitLab 里的 Commit”，而是关注“开发者 A 在项目 P 上的投入”。
* **从计算导向转向治理导向**: 通过主数据预对齐，确保所有指标计算基于同一套“人、财、组织”底座。

---

## 2. “五层五位”分层架构设计

系统采用严格的五层分层架构，通过 dbt 进行物理隔离与逻辑抽象。

### L0: ODS (Operational Data Store - 原始归集层)

* **定位**: 外部系统（GitLab, Jira, Sonar, Jenkins）原始 API 的高保真镜像。
* **形态**: `stg_` 前缀模型，主要执行字段重命名、基础类型转换，保留原始 `jsonb` 数据以备审计。

### L1: MDM (Master Data Management - 主数据层) 🌟

* **核心大脑**: 这是全系统的“单一事实源 (SSOT)”。
* **内涵**:
  * **身份中心 (Identity)**: 通过 `mdm_identities` 实现跨系统账号的归一化映射。
  * **资源拓扑 (Topology)**: 建立“项目 -> 应用 -> 代码库”的层级树。
  * **成本配置 (Financial Meta)**: 定义各职级、各团队的标准人工费率。
* **优势**: 业务逻辑变动（如人员调岗）只需在 MDM 更新，所有下层 Fact 表自动感知。

### L2: INT (Intermediate - 通用引擎层)

* **引擎化抽象**:
  * **统一活动流引擎 (`int_unified_activities`)**: 将 Commits, MRs, Issues, Comments 抽象为标准化的 Event Stream。
  * **统一工作项引擎 (`int_unified_work_items`)**: 强行拉齐 Jira 和 GitLab 的任务状态模型。
* **业务加签**: 在此层执行 **研发财务分类 (CapEx/OpEx)** 的核心逻辑推导。

### L3: DWS (Data Summary Service - 公共汇总层)

* **定位**: 以实体（人、项目、时间）为维度的指标预聚合。
* **输出**: 宽表形式，包含 DORA 核心指标、SPACE 效能、文件知识拥有度等。

### L4: ADS/MARTS (Application Data Store - 应用集市层)

* **场景驱动**: 直面 BI 看板和管理决策。
* **代表模型**: `fct_capitalization_audit` (资本化审计事实)、`fct_talent_radar` (人才雷达)、`fct_code_hotspots` (代码红区)。

---

## 3. 核心技术创新点

### 3.1 跨系统身份归一化 (Global Identity Resolution)

针对一个开发者在 GitLab 用 `alice.w`, 在 Jira 用 `alice_wang` 的问题，系统建立了 `mdm_identity_mappings` 机制，通过权重算法实现自动挂载，并在 dbt 计算中通过 `int_identity_alignment` 进行无感知替换。

### 3.2 研发活动之“事件化”抽象

系统将所有的研发行为标准化为：
`[时间戳, 发起者, 活动类型, 目标实体, 影响分值, 元数据]`
这种抽象使得计算“开发者画像”变得异常简单：仅需在统一活动流上进行 `count(*)` 或 `sum(impact)`。

### 3.3 自动化财务核算自动化 (Value Stream Accounting)

基于 `int_activity_financial_classification` 模型，系统通过语义识别和关联任务类型：

* **资本化 (CapEx)**: 挂载需求、功能的变更。
* **费用化 (OpEx)**: 修复 Bug、处理债务、线上支持。
这使得每张报表都具备“审计穿透力”，可从财务金额直接穿透到具体的代码 Commit。

---

## 4. 数据治理与质量保证

为确保架构的健壮性，引入了“双重守卫”：

1. **单元测试 (Unit Tests)**: 针对转换层 (`int_`) 的复杂逻辑（如财务分类、DORA Leadtime 计算）编写 Mock 案例，确保代码修改不破坏业务定义。
2. **架构测试 (Data Tests)**:
    * **主键唯一性**: 确保 Fact 表无重复数据。
    * **关系引用**: 确保所有应用数据都能回溯到 MDM 主数据。
    * **值集验证**: 确保 `audit_status` 等字段符合枚举规范。

---

## 5. 技术栈支撑 (Tech Stack)

* **建模工具**: dbt (Data Build Tool) 1.8+
* **仓库底座**: PostgreSQL 16 (支持向量化与 JSONB 索引)
* **调度引擎**: Dagster (软件定义资产 SDA)
* **元数据治理**: DataHub
* **质量监控**: Great Expectations

---

## 6. 结语

本架构通过“分而治之”的设计方案，将不稳定的工具数据转化为稳定的业务资产，为组织提供了高可信、可穿透、可扩展的研发数字化基石。

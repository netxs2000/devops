# DevOps 效能平台需求规格说明书 (SRS)

**项目名称**: DevOps Data Collector & Analytics Platform
**版本**: 3.9.0 (Modernized Data Platform)
**日期**: 2026-01-02
**密级**: 内部公开

---

## 1. 引言 (Introduction)

### 1.1 编写目的

本文档旨在明确 **DevOps 效能平台** 的功能需求、非功能需求及接口规范，为开发团队、测试团队及项目干系人提供统一的执行标准。

### 1.2 背景

当前研发管理面临数据分散（GitLab/SonarQube/Jenkins/Jira 割裂）、指标主观（缺乏 DORA 等量化标准）、协作黑盒（无法感知真实工作量与瓶颈）等痛点。本系统通过引入 **Dagster** 编排引擎与 **dbt** 数据建模技术，构建了高可观测、可审计、且具备治理能力的数据资产产线。

### 1.3 适用范围

本系统适用于研发中心所有产研团队，覆盖需求、开发、测试、部署、运营全生命周期。

---

## 2. 总体描述 (Overall Description)

### 2.1 产品愿景

打造企业级研发效能“驾驶舱”，通过数据驱动研发效能提升，实现：

* **软件定义资产 (SDA)**: 每一份指标报表都是受控、可回溯的数据资产。
* **数据血缘透明**: 利用 Dagster 与 DataHub 实现从原始 API 到最终 ROI 报表的全链路血缘追踪。
* **可审计**: 实现研发投入 (FinOps) 与业务产出 (Contracts) 的量化对齐，支持 R&D 资本化审计。

### 2.2 用户角色

| 角色 | 职责 | 核心诉求 |
| :--- | :--- | :--- |
| **研发工程师** | 代码开发、CR、修复 Bug | 查看个人产出画像、技术债预警、MR 风险 AI 评级 |
| **Tech Lead** | 团队管理、技术决策 | 监控项目进度、识别架构脆性、进行研发投入资本化核算 |
| **PMO/管理层** | 效能度量、资源协调 | 查看部门 ROI 记分卡、战略组合矩阵、人才能力雷达 |
| **数据治理员** | 元数据维护、质量监控 | 监控模型血缘、配置 GE 质量巡检、全文检索数据索引 (DataHub) |

### 2.3 系统架构

系统采用 **现代数据栈 (Modern Data Stack)** 架构：

* **Orchestration (Dagster)**: 负责全链路任务编排、资源隔离与资产状态管理。
* **Collection (Plugins)**: 负责从各系统采集 Raw Data，并存储于 Staging 层。
* **Transformation (dbt)**: 负责将 Staging 层数据转换为标准化的维度模型 (Dimensional Models) 与指标。
* **Governance (DataHub & GE)**: 负责元数据目录管理与数据质量断言。
* **Serving (FastAPI & Streamlit)**: 提供标准 API 服务与动态交互式数据仪表盘。

---

## 3. 功能需求 (Functional Requirements)

### 3.1 数据采集与同步 (R-COLLECT)

#### R-COLLECT-01: 多源数据适配

* **描述**: 支持主流研发工具（GitLab, Jira, SonarQube, Jenkins, ZenTao, JFrog, Nexus）的 API 深度对接。

#### R-COLLECT-02: 软件定义采集 (SDA)

* **描述**: 利用 Dagster Assets 定义采集任务，支持按资产依赖关系自动触发增量同步。

#### R-COLLECT-03: 元数据治理 (DataHub)

* **描述**: 自动将采集到的表结构、字段说明、任务状态同步至 DataHub，提供统一的数据搜索入口。

### 3.2 数据处理与模型 (R-PROCESS)

#### R-PROCESS-01: 统一身份与 SCD Type 2

* **描述**: 建立 OneID 身份映射。对关键实体（Org, User, Service）采用 **SCD Type 2 (渐变维)** 存储，保留历史快照用于趋势分析。

#### R-PROCESS-02: dbt 模型化建模

* **描述**: 采用 dbt 实现多层建模（Base -> Int -> Fct），所有计算逻辑 SQL 化、代码化、版本化。

#### R-PROCESS-03: 数据质量哨兵 (Great Expectations)

* **描述**: 在模型产出过程中集成 GE 校验规则，防止脏数据流入下游报表。

### 3.3 效能洞察与分析 (R-ANALYTICS)

#### R-ANALYTICS-01: DORA & 流动效能

* **描述**: 深度追踪任务在各状态的停留时间，计算 **Flow Efficiency** 及 DORA 四大指标。

#### R-ANALYTICS-02: 研发投入产出比 (ROI) 🌟

* **描述**: 结合 `mdm_calendar` 核算精确人力工时，计算各层级（项目/产品/业务线）的 ROI 效能得分。

#### R-ANALYTICS-03: AI 智能增强

* **描述**: 对 Merge Request 进行风险评级，对非结构化任务描述进行自动化语义分类。

#### R-ANALYTICS-04: 合规与架构

* **描述**: 监控研发红线违规、识别架构脆性指数 (ABI)、进行开源许可证审计。

---

## 4. 非功能需求 (Non-Functional Requirements)

### 4.1 性能与可观测性

* **观测性**: 所有 Dagster Job 必须能实时追踪 Run ID 及日志。
* **幂等性**: 所有数据转换任务须支持重跑，遵循原子性原则。

### 4.2 可扩展性

* **模型扩展**: 支持通过新增 dbt 模型快速生成新指标。
* **接入扩展**: 新插件仅需遵循 Python ORM 规范即可无缝注册至 Dagster 编排图谱。

---

## 5. 接口需求 (Interface Requirements)

### 5.1 数据 Serving 接口

* 系统通过 **dbt-generated tables/views** 暴露核心报表数据。
* FastAPI 门户作为交互式后台，提供实时工单推送 (SSE) 与 过程治理 API。

### 5.2 编排引擎接口

* 外部触发接口：支持向 Dagster Daemon 发送 GraphQL 请求或使用 Webhook 触发特定资产更新。

---

## 6. 附录 (Appendix)

* 《DevOps Data Dictionary (DATA_DICTIONARY.md)》
* 《Dagster & dbt Deployment Guide》
* 《FinOps ROI Calculation Logic Spec》

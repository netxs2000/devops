# 系统架构设计文档 (System Architecture Design)

**版本**: 4.0.0 (Refactored)
**日期**: 2026-01-04

## 1. 架构概览 (Architecture Overview)

DevOps Data Collector 已由传统的 ETL 演进为基于 **Modern Data Stack (MDS)** 的软件定义资产架构。系统核心通过 **Dagster** 驱动，实现从数据采集到业务洞察的全链路自动化编排。

系统的核心流转逻辑：

1. **编排层 (Orchestration Layer)**: 由 **Dagster** 统一管理任务调度，通过 SDA (Software Defined Assets) 实现数据血缘驱动的自动化更新。
2. **采集层 (Collection Layer)**: 插件化适配器 (`BaseWorker`)，执行外部 API 数据抽取。
3. **主数据层 (MDM Layer) 🌟**: **架构核心**。管理身份 (Identity Resolution)、组织、项目拓扑等核心元数据，作为全系统的单一事实源 (SSOT)。
4. **转换层 (Transformation Layer) 🌟**: 利用 **dbt** 构建五层数仓模型 (ODS -> MDM -> INT -> DWS -> MART)，实现逻辑封装。
5. **治理层 (Governance & Metadata) 🌟**: 集成 **DataHub** 和 **Great Expectations**。提供自动化全链路血缘视图与数据质量实时监控。
6. **服务层 (Service Layer)**: 数据集市 (Data Mart)，通过 dbt 生成的五层物化模型提供高性能 API 和 BI 接入点。
7. **交互层 (Interaction Layer)**:
    * **Interactive Portal**: FastAPI + Vanilla JS 高性能管理门户。
    * **Advanced Analytics**: Streamlit 驱动的深度业务透视看板。

```mermaid
graph TD
    subgraph Orchestration [编排与管控]
        DS[Dagster SDA]
        GE[Great Expectations]
    end

    subgraph Data Sources
        API[GitLab/Jira/Sonar/Jenkins]
    end

    subgraph Processing [存储与建模]
        ODS[(ODS - Raw Staging)]
        MDM[(MDM - Master Data Center)]
        DBT[[dbt Transformation Engine]]
        DWH[(DWH - Layered Tables)]
    end

    subgraph Governance [元数据与治理]
        DH[DataHub Catalog]
    end

    subgraph Presentation [应用与展示]
        PORTAL[Fastapi Portal]
        BI[Streamlit Analytics]
    end

    API -->|Extract| ODS
    ODS -->|Refine| DBT
    MDM -->|SSOT Support| DBT
    DS -->|Schedules| DBT
    DBT -->|Materialize| DWH
    DWH -->|Lineage| DH
    GE -.->|Data Quality| DWH
    DWH -->|Serve| PORTAL
    DWH -->|Serve| BI
```

## 2. 核心设计理念 (Core Concepts)

### 2.1 软件定义资产 (Software-Defined Assets) 🌟

系统摒弃了“先跑任务，再产出文件”的模式，转而使用 Dagster 定义资产的最终状态。

* **血缘透明**: 每一项指标（如 ROI）都可以追溯到其依赖的 dbt 模型，进而追溯到原始 API 数据。
* **按需更新**: 系统能智能识别哪些资产已过期，仅重跑受变动影响的部分，极大节省 IO 资源。

### 2.2 统一身份认证 (Unified Identity & SCD Type 2)

为了解决跨工具账号隔离与历史变动追踪：

* **SCD Type 2 (渐变维)**: 核心主数据（用户、组织、成本配置）采用“生效/失效日期”管理模式。通过 `close_current_and_insert_new` 统一服务，确保历史效能数据在人员调岗、部门合并后依然可准确回溯。
* **乐观锁机制**: 采用 `version` 字段防止多节点并发采集导致的数据冲突。

### 2.3 分析逻辑下沉 (Transform via dbt)

采用 "ELT" 思维，将所有的指标计算逻辑（Metrics Definitions）从应用层移至 **dbt**。

* **模型层次化**: 严格遵循 `stg` (清理), `mdm` (对齐), `int` (引擎化), `dws` (汇总), `marts` (事实) 五层架构。
* **文档化与测试**: 引入 dbt Unit Tests 验证业务逻辑，dbt Schema Tests 验证主键与关系完整性。

### 2.4 数据质量守卫 (Data Quality Guard)

集成 **Great Expectations (GE)** 在数据进入核心表前进行颗粒度校验：

* **非空校验**: 确保关键 ID（如 `global_user_id`）不丢失。
* **一致性校验**: 确保 dbt 转换后的产出物符合业务常识（如 ROI 不能为负）。

## 3. 编排与同步流程 (Orchestration Flow)

### 3.1 资产流水线 (Asset Pipeline)

1. **Ingestion Assets**: 运行 Plugin Worker，抽取 GitLab/Jira 原始数据。
2. **Harmonization Assets**: 进行身份归一、组织树挂载、地理位置映射。
3. **Verification Assets**: 调用 GE 执行质检。
4. **Analytics Assets (dbt)**: 触发 dbt run，生成 ROI、资本化、DORA 等物化模型。
5. **Metadata Capture**: 将运行日志与血缘推送至 DataHub。

### 3.2 增量同步逻辑

* **时间窗口机制**: 通过 Dagster Partition 实现按日/按周重跑特定时间窗口的数据。
* **Webhook 触发**: 利用 FastAPI Webhook 监听 GitLab 事件，实时触发 Dagster 操作节点 (Op) 进行局部资产刷新。

## 4. 财务、ROI 与成本核算 (FinOps & Traceability)

系统建立了从“原始需求 -> 代码变更 -> 自动化测试 -> 版本发布 -> 财务对账”的全链路追踪：

* **精准归责**: 结合 `mdm_calendar` 工作日模型，扣除国家法定节假日，实现最真实的投入产出比核算。
* **AI 风险驱动**: 集成 AI 模型对合并请求 (Merge Request) 进行分类。若识别为“紧急修复”或“回归 Bug”，则在统计效能时自动应用更高的复杂度权重。

## 5. 扩展性与治理 (Extensibility & Governance)

* **Plugin 插件化**: 新增外部系统只需继承 `BaseWorker` 并注册至 `PluginRegistry`。
* **元数据透明**: 任何数据字段的变动通过 dbt 自动扩散至全局文档，开发者可通过 DataHub 搜索任何指标的口径定义。

## 6. 技术栈总结 (Technology Stack)

* **Orchestrator**: Dagster
* **Transformation**: dbt
* **Database**: PostgreSQL 16
* **Validation**: Great Expectations
* **Backend**: FastAPI (Python 3.11+)
* **Frontend**: Vanilla JS (Portal) + Streamlit (Analytics)
* **Messaging**: RabbitMQ / SSE
* **Governance**: DataHub

# 系统架构设计文档 (System Architecture Design)

## 1. 架构概览 (Architecture Overview)

DevOps Data Collector 采用模块化的**ETL (Extract, Transform, Load)** 架构，旨在实现高扩展性、高可靠性和数据的一致性。

系统的核心流转逻辑：
1.  **采集层 (Collection Layer)**: 插件化适配器，实现 `BaseWorker` 标准接口，负责对接 API 并执行 **Extract**。
2.  **暂存层 (Staging Layer)** 🌟: 近实时地将原始 JSON 响应落盘至 `raw_data_staging` 表，作为 ETL 的 ODS 层，确保数据的原始性与可重放性。
3.  **核心层 (Core Layer)**: 负责数据清洗、实体关联、身份归一化、任务分发 (RabbitMQ) 和 **Transform/Load**。
4.  **存储层 (Storage Layer)**: 关系型数据库 (PostgreSQL) 存储结构化基础数据 (Fact Tables)。
5.  **增强层 (Enrichment Layer)** 🌟: 利用 **LLM (大语言模型)** 对 Work Items 和 Commits 进行自动分类与摘要，为 ROI 分析提供业务语义。
6.  **财务层 (FinOps Layer)** 🌟: 建立 CBS (Cost Breakdown Structure) 科目树，将技术里程碑与合同回款节点挂钩。
7.  **服务层 (Service Layer)**: 数据集市 (Data Mart)，通过 SQL Views 封装复杂的分析逻辑（如 DORA, 战略矩阵），直接对接 BI。

```mermaid
graph TD
    subgraph Data Sources
        API[GitLab/Jira/Jenkins/Sonar/ZenTao API]
    end

    subgraph Collection & Staging [采集与暂存]
        PW[Plugin Worker]
        STG[(Raw Data Staging<br>JSON ODS)]
    end

    subgraph Core Processing [核心处理与清洗]
        IM[Identity Matcher]
        OM[Org Manager]
        SCH[Pydantic Validation]
    end

    subgraph Storage & Analytics [存储与分析]
        DB[(PostgreSQL Fact Tables)]
        DM[Analytics Views<br>Data Mart]
        DBT[dbt Transformations]
    end

    API -->|Extract| PW
    PW -->|Immediate Save| STG
    STG -->|Replay/Transform| SCH
    SCH -->|Clean Data| IM
    IM -->|Relational Load| DB
    DB -->|Model Logic| DBT
    DBT -->|Materialized| DM
    
    note right of STG
      Schema Versioning
      (v1.0, v1.1...)
    end note
    
    note right of STG
      Schema Versioning
      (v1.0, v1.1...)
    end note
```

## 2. 核心设计理念 (Core Concepts)

### 2.1 统一身份认证 (Unified Identity)
为了解决工具间账号不互通的问题（例如 GitLab 用户名为 `zhangsan`，SonarQube 为 `zs001`），系统引入了 `users` 全局用户表。
*   **机制**: 优先基于 **Email** 进行匹配。
*   **虚拟用户**: 对于外部贡献者（无公司邮箱），标记 `is_virtual=True`，允许手动维护。

每个数据源作为一个独立的 Plugin 存在，必须实现标准接口，并通过 `PluginRegistry` 统一注册：
*   **Registry 工厂模式**: 核心代码不再硬编码具体 Client。Worker 在运行时通过 `get_client_instance` 和 `get_worker_instance` 动态构建对象。
*   `collect_projects()`: 发现项目。
*   `sync_data()`: 执行同步逻辑。

### 2.3 分析逻辑下沉 (Analytics in Database)
我们采用 "ELT" 而非传统的 "ETL" 思维处理复杂指标。
*   **Python 代码** 仅负责将原始数据原样搬运到数据库 (Load)。
*   **SQL Views** 负责所有的业务逻辑计算（如“计算 DORA 指标”、“识别僵尸项目”）。
*   **SQL Views** 负责所有的业务逻辑计算（如“计算 DORA 指标”、“识别僵尸项目”）。
*   **优势**: 修改指标定义无需重新部署代码，且利用数据库引擎聚合性能更高。

### 2.4 原始数据回溯 (Raw Data Replay) 🌟
系统引入 `SCHEMA_VERSION` 机制，所有原始 API 响应在进入业务表前，先带有版本号（如 v1.0, v1.1）落盘至 `raw_data_staging`。
*   **Schema Evolution**: 当 API 结构变更时，Worker 升级 `SCHEMA_VERSION`，已有旧版本数据不受影响。
*   **Data Replay**: 利用 `scripts/reprocess_staging_data.py`，可在不重新请求外部 API 的情况下，读取 Staging 表并应用新的清洗逻辑（如修复 Bug 或增加字段）。

## 3. 数据流设计 (Data Flow)

### 3.1 初始化阶段 (Discovery)
1.  运行 `init_discovery.py`。
2.  遍历 GitLab 顶层 Group，构建 `organizations` 树。
3.  扫描所有 Project，写入 `projects` 表（仅元数据）。

### 3.2 增量同步阶段 (Incremental Sync)
1.  **GitLab 采集 (流式 & 分批)**:
    *   **流式拉取**: 利用 Python Generator 逐页获取数据。
    *   **分批处理**: 每 500 条记录构建 Batch。
    *   **幂等写入**: Upsert 策略，支持随时断点续传。
    *   **深度分析模式 (Deep Analysis)**: 采集 Issue 事件流 (Events) 并通过 `IssueStateTransition` 重建流转历史，支持 **Cycle Time** 和 **Flow Efficiency** 计算。
    *   **阻塞识别**: 自动化提取 'blocked' 标签的时段，计算**阻塞时长**。
2.  **AI 增强分析**:
    *   针对同步完成的 MR/Issue/Commit，调用 `EnrichmentService` 进行智能分类 (AI Category)。
3.  **SonarQube 采集**:
    *   关联 GitLab 项目，拉取 Quality Gate 与 Metrics。
4.  **Jenkins 采集**:
    *   同步 Job 列表，抓取 Build 详细记录（时长、结果、触发者）。

## 4. 财务与 ROI 架构 (FinOps & ROI Design) 🌟 (New)

系统通过“CBS -> Project -> Labor/Infra”链路实现全量研发成本分摊：
*   **成本采集**: 基建成本来自采购合同摊销，人工成本根据职级与标准费率计算。
*   **产出对齐**: 收入合同挂载收款节点，每个节点映射一个 GitLab Milestone。当里程碑关闭时，视为产出动作达成。
*   **ROI 计算**: `(合同回款额 / 投入成本)` 决定项目在波士顿矩阵中的 Y 轴坐标。

## 5. 关键技术决策 (Key Decisions)

*   **为什么全用 SQL View 做报表？**
    *   **性能**: 对于数百万级 Commits 的聚合，数据库（尤其是 PG）比 Python Pandas 更高效，且无需数据搬运。
    *   **开放性**: 任何该支持 SQL 的 BI 工具 (Superset, Tableau, PowerBI) 都可直接接入，无需开发 API。
    *   **一致性**: SQL 脚本即文档，指标定义清晰可见 (Single Source of Truth)。

*   **为什么使用 RabbitMQ？**
    *   **削峰填谷**: 应对突发的大规模同步请求。
    *   **解耦**: 调度层 (Scheduler) 与执行层 (Worker) 分离，支持多机器部署 Worker 提升并发性能。
    *   **可靠性**: 任务失败可自动重回队列，确保每一条数据都不丢失。

*   **大批量数据适配**
    *   **Generator Stream**: 内存占用 O(1)。
    *   **Batch Commit**: 兼顾写入性能与事务安全。

## 5. 扩展性设计 (Extensibility)
系统采用“注册驱动”模式。如需添加新指标（如“代码注释率”）：
1.  **Schema**: 修改 `models/` 增加字段。
2.  **Plugin**: 在插件目录下扩展 `analyzer.py` 或 `identity.py` 逻辑。
3.  **Collector**: 修改 Plugin 填充字段。
4.  **Analytics**: 修改 `sql/PROJECT_OVERVIEW.sql` 视图定义即可生效。

# DevOps 平台架构白皮书：现代数仓与主数据驱动的研发效能引擎

> **版本**: v3.0 (2026-01-04)  
> **语言**: 中文 (Chinese)  
> **核心组件**: Python Pydantic V2, PostgreSQL, dbt (1.8+), MDM OneID  

---

## 1. 架构总览 (Architectural Overview)

本平台采用 **ELT (Extract-Load-Transform)** 模式驱动，通过 **现代数据仓库 (Modern Data Warehouse)** 架构实现全链路研发数据的采集、治理与价值落地。架构重构的核心目标是消除“数据孤岛”和“身份歧义”，构建一套可扩展、高可信的研发效能度量引擎。

### 1.1 核心设计理念

* **逻辑与采集解耦**: Python 采集端（Collector）仅负责获取原始数据（Load），复杂的指标计算移交给数仓转换层（Transform）。
* **身份主导 (OneID)**: 所有的活动流（Commits, MRs, Tasks）强制挂载到全局唯一的 MDM 身份标识上。
* **代码即资产**: 基于 dbt 实现 SQL 逻辑的模块化、版本化与自动化测试。

---

## 2. 分层架构详解 (Layered Architecture)

### 2.1 原始数据层 (L1 - ODS / Raw Data)

* **职能**: 保持原始数据的“原生态”存储，作为“数据时光机”支持逻辑重演。
* **实现**: 由 Python 高性能 Worker (Pydantic V2 + SQLAlchemy) 写入 PostgreSQL 物理表。
* **表前缀**: `gitlab_*`, `sonar_*`, `jenkins_*`, `jira_*`。

### 2.2 主数据管理层 (L2 - MDM Core)

* **职能**: 定义系统的“单一事实来源 (Single Source of Truth)”，解决跨系统实体识别问题。
* **核心实体**:
  * **mdm_identities**: 存储员工 OneID，关联 GitLab/Jenkins/Email 账号。
  * **mdm_organizations**: 维护部门层级与汇报线。
  * **mdm_entities_topology**: 维护“应用-代码库-服务”的映射关系。
  * **mdm_resource_costs**: 存储资源费率，用于 ROI 计算。

### 2.3 dbt 基础建模层 (L3 - Staging Layer)

* **职能**: 数据清洗与字段重构。
* **关键变更**: 屏蔽源表字段缩写，统一日期格式，剔除软删除记录。
* **命名规范**: `stg_<source>_<entity>`。

### 2.4 dbt 业务集成层 (L4 - Intermediate Layer)

* **职能**: 构建中性、通用的业务模型。
* **核心模型**:
  * **int_unified_activities**: 统一活动流模型，将 Commit、MR、Notes、Issue 动作打平为一个标准的事件序列。
  * **int_sonarqube_scans**: 校准 Sonar 扫描数据，对齐项目引用关系。
* **重构重点**: 实现了对 Jenkins 指标的“事件化处理”，替代了原有的硬编码聚合。

### 2.5 dbt 度量汇总层 (L5 - DWS Layer)

* **职能**: 多维指标的预聚合，提升前端响应性能。
* **模型示例**:
  * **dws_project_metrics_daily**: 每日项目交付与质量汇总看板（包含 mrs_opened, prod_deploys, bug_count）。
  * **dws_developer_metrics_daily**: 开发者每日活跃度汇总。
  * **dws_space_metrics_daily**: 根据 SPACE 框架预计算五个维度的每日得分。

### 2.6 应用事实层 (L6 - Marts / Fact Layer)

* **职能**: 对接最终应用看板，承载业务规则定义。
* **核心模型**:
  * **fct_dora_metrics**: 最终的 DORA 指标表（DF, LTFC, MTTR, CFR）。
  * **fct_talent_radar**: 用于人才画像识别的影响力矩阵。
  * **fct_capitalization_audit**: 专供财务审计的研发投入核算模型。

---

## 3. 核心机制：身份解析与 OneID

架构重构最大的技术突破在于 **身份对齐算法**。

1. **自动发现**: 通过 Email 和 Username 在 Intermediate 层自动关联 ODS 数据。
2. **映射机制**: 存储在 `mdm_identity_mappings` 中。
3. **计算逻辑**: 所有的 DWS 汇总模型不再依据 `gitlab_user_id`，而是通过 `ref('int_gitlab_user_mapping')` 关联到 `master_user_id`。

---

## 4. 质量校验哨兵 (Data Quality Framework)

新架构通过 **三级测试体系** 确保数据的工业级可信度：

1. **Schema Tests (静态约束)**:
    * 强制源表与汇总表的关键字段满足 `unique` 和 `not_null`。
    * 验证外键关系的引用一致性。
2. **Unit Tests (逻辑单元测试)**:
    * 利用 dbt 1.8 特性，通过静态 Mock 数据验证复杂 SQL（如 DORA 计算）的准确性，确保“重构不破坏原有逻辑”。
3. **Singular Tests (业务规则审计)**:
    * 自定义 SQL 校验，如：`dws` 层的聚合值不应超过 `ods` 的物理总量，防止数据多算。

---

## 5. 架构演进收益 (Benefits)

| 维度 | 重构前 | 重构后 (v3.0) |
| :--- | :--- | :--- |
| **可扩展性** | 每加一个数据源都要修改 Python 核心逻辑 | 仅需增加 Staging 映射，其余利用 dbt 自动流转 |
| **可维护性** | 复杂的业务逻辑分散在几十个 SQL 文件中 | 逻辑层级清晰，代码可重用性提升 70% |
| **准确性** | 基于原始账号，离职或改名后数据断裂 | 基于 OneID，实现人员全生命周期的活动记录追溯 |
| **开发效率** | 缺乏测试，线上错误难调试 | 变更前跑通 Unit Tests，实现“变更自信” |

---

## 6. 未来展望

* **实时化**: 引入 dbt + Materialize 模式探索秒级指标采集。
* **自治化**: 基于 DataHub 自动同步数仓元数据与血缘，实现研发资产的自助发现。

---
**DevOps Architecture Group**  
**2026-01-04**

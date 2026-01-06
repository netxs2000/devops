# 数据治理白皮书 (Data Governance Whitepaper)

**版本**: 4.0.0 (Refactored Edition)  
**日期**: 2026-01-06

## 1. 治理愿景

确保 DevOps 效能平台产出的每一项指标都是**软件定义资产 (SDA)**。通过 **Dagster** 的强编排与 **DataHub** 的全链路血缘，实现数据从“采集 -> 建模 -> 消费”的全生命周期可观测性与合规性。

## 2. 身份与主数据治理 (MDM & Identity)

### 2.1 归一化与 SCD Type 2

* **OneID 归一化**: 通过 `IdentityManager` 对多源账号进行强对齐。
* **渐变维 (SCD Type 2)**: 针对组织架构 (`mdm_organizations`) 和 人员主数据 (`mdm_identities`) 采用 SCD Type 2 存储。系统必须保留历史记录，确保“去年的审计报表能对齐去年的组织架构”，严禁直接覆盖历史实体的业务属性。

### 2.2 日历治理 (MDM Calendar)

* **核算基准**: 所有涉及“Cycle Time”或“Labor Cost”的计算必须挂载 `mdm_calendar`。
* **治理规则**: 严禁将法定节假日计入研发有效工时，确保 ROI 计算的客观性。

## 3. 建模与模型治理 (Model Governance)

### 3.1 dbt 建模标准

* **层级隔离**: 严格遵循 `base -> intermediate -> mart` 三层建模。
  * `Base`: 仅做基础重命名与类型转换。
  * `Intermediate`: 进行跨域关联（如 Issue 与 Commit 关联）。
  * `Mart`: 产出最终业务指标。
* **代码合规**: 所有的模型逻辑必须经过 Pull Request 审计，且必须包含 dbt-test。

### 3.2 元数据目录 (DataHub)

* **血缘要求**: DataHub 中必须能清晰看到指标报表的上游原始数据表依赖。

### 3.3 命名冲突治理 (Conflict Resolution)

* **模型隔离原则**: 严禁模型命名与系统工具（如测试框架、构建引擎）产生重名冲突。所有测试管理资产统一使用 `GTM_` 前缀，确保存储层与工具链的逻辑纯度。
  * 案例：`TestCase` -> `GTMTestCase`
  * 案例：`Requirement` -> `GTMRequirement`

## 4. 数据质量治理 (Data Quality)

### 4.1 自动化质量检查 (Great Expectations)

系统在数据管道的关键节点集成 **GE (Great Expectations)** 断言：

* **Schema 校验**: 原始 JSON 必须满足 Pydantic V2 定义。
* **业务校验**:
  * `expect_column_values_to_not_be_null`: 关键关联键（如 `user_id`, `project_id`）严禁为空。
  * `expect_column_values_to_be_between`: 费率、活跃率等指标必须在业务合理区间。
  * `expect_column_values_to_match_regex`: 版本号、工号等需符合正向标准。

### 4.2 质量红线

若 Dagster Asset Check 判定为“失败”，则该资产的状态将被标记为“非受信任”，相关的 BI 报表必须显示“数据质量预警”水印。

## 5. 存储与归档政策

### 5.1 软件定义存储

* **Raw Layer**: `raw_data_staging` 存储原始报文，保留 30-90 天。
* **Curated Layer**: 结构化事实数据，保留 2 年以上，支持通过 dbt 重新计算全历史数据。

## 6. 权限与隐私控制

* **OneID 隔离**: 对包含个人敏感信息的字段进行 RBAC 权限隔离。
* **资产可见性**: 根据 DataHub 中的资产标记（Public/Internal/Secret）控制不同角色的访问权限。

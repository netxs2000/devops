# DevOps 数据平台全面验收报告 (模板)

## 1. 验收概述

* **项目名称**: DevOps 数据平台深层重构
* **验收时间**: {{ 验收日期 }}
* **验收环境**: 本地测试环境 / CI 流水线
* **dbt 版本**: 1.8.x

## 2. 核心逻辑验证 (单元测试)

通过 `dbt unit-test` 模拟边界数据，验证复杂业务逻辑的准确性。

| 测试场景 | 验证模型 | 状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **研发活动财务分类** | `int_activity_financial_classification` | [ 待测试 ] | 验证 Feature -> CapEx, Bug -> OpEx 等路由逻辑 |
| **资本化率计算** | `fct_capitalization_audit` | [ 待测试 ] | 验证公式：`capex / total_impact` 及其四舍五入 |
| **标识符引用校验** | `fct_metrics_audit_guard` | [ 待测试 ] | 验证非法项目 ID 的过滤逻辑 |

## 3. 数据质量约束 (架构测试)

运行 `dbt test` 验证模型字段约束及引用完整性。

| 测试项 | 覆盖模型 | 评估标准 | 结果 |
| :--- | :--- | :--- | :--- |
| **唯一性 (Unique)** | `fct_*`, `dws_*` (PK) | 主键不重复 | [ 待测试 ] |
| **非空 (Not Null)** | `*_id`, `occurred_at` | 核心字段无缺失值 | [ 待测试 ] |
| **枚举值 (Accepted Values)** | `audit_status`, `category` | 符合预设状态值集 | [ 待测试 ] |
| **关系引用 (Relationship)** | `marts` -> `mdm` | 外键存在且一致 | [ 待测试 ] |

## 4. 链路血缘分析 (Lineage)

* **深度检查**: 从 `stg_gitlab_*` 到 `fct_capitalization_audit` 的链路是否完整？
* **结果**: [ 正常 / 异常 ]
* **关键断点检查**: `int_unified_activities` 已整合 Commit, MR, Issue, Note 四大源流。

## 5. 验收结论

* [ ] **通过**: 所有测试用例通过，满足业务生产要求。
* [ ] **有条件通过**: 部分次要测试项失败，但不影响核心交付。
* [ ] **不通过**: 核心逻辑存在偏差，需重构后重新验收。

---
**核准人**: Antigravity (AI Assistant)
**日期**: 2026-01-04

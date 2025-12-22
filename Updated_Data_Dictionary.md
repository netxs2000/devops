# 集团研发主数据字典 v4.0 (MDM 增强版)

## 1. 全局身份索引表 (`mdm_identities`)
| 字段 | 类型 | 描述 | 说明 |
| :--- | :--- | :--- | :--- |
| `guid` | UUID | 全局唯一标识 | 主键，关联所有子系统记录 |
| `emp_id` | String | HR 工号 | 权威源主键 |
| `id_map` | JSONB | 账号映射集 | `{"gitlab": 1, "jira": "u123"}` |

## 2. 研发资产表 (`mdm_assets`)
| 字段 | 类型 | 描述 | 说明 |
| :--- | :--- | :--- | :--- |
| `asset_id` | UUID | 资产 ID | 对应代码库或组件库 |
| `tech_labels` | Array | 技术栈标签 | `[Java, Vue, Redis]` |
| `is_core` | Boolean | 核心资产 | 用于关键资产统计 |

## 3. 财务维度表 (`fin_cost_allocation`)
| 字段 | 类型 | 描述 | 说明 |
| :--- | :--- | :--- | :--- |
| `project_id` | UUID | 项目 ID | 关联项目主表 |
| `capex_ratio` | Numeric | 资本化比例 | 财务结项使用 |
| `labor_cost` | Numeric | 人力成本 | 自动计算：工时 * 职级单价 |

## 4. 指标元数据 (`metric_metadata`)
| 字段 | 类型 | 描述 | 示例 |
| :--- | :--- | :--- | :--- |
| `metric_code` | String | 指标代码 | `CYCLE_TIME_AVG` |
| `formula` | Text | 计算逻辑 | `avg(deploy_date - commit_date)` |
| `owner_dept` | String | 指标归口部门 | PMO / QA |
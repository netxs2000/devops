# dbt 数据建模开发规范 (DBT Modeling Guide)

> **版本**: 1.1
> **更新日期**: 2026-03-16
> **适用范围**: 所有 dbt 模型的开发与维护

## 1. 层次结构与职责 (Layering & Responsibility)

| 层级 | 前缀 | 职责描述 | 数据形态 |
| :--- | :--- | :--- | :--- |
| **Staging** | `stg_` | **原始清洗层**：1:1 映射 Source，完成字段改名、基本类型转换及非标空值处理 (0 -> NULL)。 | 扁平模型，与源系统同构 |
| **Intermediate** | `int_` | **中间转换层**：跨源关联、身份/组织归一化、复杂业务逻辑组合（如 DORA 指标预计算）。 | 归一化后的业务实体片段 |
| **Marts** | `dim_` / `fct_` | **结果交付层**：`dim_` 为业务维度；`fct_` 为事实指标表。直接对接 Superset/Streamlit。 | 星型/雪花型建模 |

## 2. 命名契约 (Naming Convention)

### 2.1 模型文件命名
- **Staging**: `stg_{source}_{resource}.sql` （例：`stg_gitlab_commits.sql`）
- **Intermediate**: `int_{domain}_{logic}.sql` （例：`int_org_normalization.sql`）
- **Marts**: `dim_{entity}.sql` 或 `fct_{metric_event}.sql` （例：`fct_dora_metrics_v2.sql`）

### 2.2 字段命名
- **布尔值**: 强制使用 `is_` 或 `has_` 前缀（如 `is_deleted`, `has_incident`）。
- **时间戳**: 统一使用 `_at` 后缀（如 `created_at`）。日期（不含时间）使用 `_date`。
- **ID 标识符**:
    - 主键统一命名为 `{resource}_id`。
    - 跨系统主键在 `int_` 层必须归一化为 `global_user_id` 或 `master_project_id`。

## 3. 编码防御规范 (Defensive Coding) [MANDATORY]

### 3.1 JSONB 解析与类型守卫
针对从源系统 `raw_data` (JSONB) 提取的字段，必须执行以下“三板斧”清理：
```sql
-- 推荐模板
coalesce(
    nullif(trim(both '"' from raw_data->>'resolvedDate'), ''),
    '1970-01-01'::text
)::timestamp as resolved_at
```
1. **`trim(both '"' from field)`**: 清除 JSON 字面量中可能残留的引号。
2. **`nullif(..., '')`**: 将空字符串转换为真正的 `NULL`。
3. **`coalesce`**: 为关键计算字段提供默认值。

### 3.2 ID 原子化与关联
- **类型对齐**: 跨源关联时，所有 ID 字段在 Staging 层统一转换为 `text` 类型，防止 `integer = varchar` 报错。
- **归一化优先**: 严禁在 Marts 层直接使用 GitLab URL 或 ZenTao 内部 ID。必须在 `int_` 层通过 `int_project_resource_map` 映射为主项目 ID (`PROJ-xxx`)。

## 4. 性能与资源控制 (Performance)

- **并发限制**: 在资源受限环境执行 `dbt build` 时，必须添加 `--threads 1` 参数或在 `profiles.yml` 中配置，防止 PostgreSQL 连接溢出。
- **物化策略**:
    - `stg_` 层默认使用 `view`。
    - 涉及大量计算的 `fct_` 或 `int_` 层建议使用 `table` 或 `incremental`。

## 5. 测试与元数据 (Testing & Metadata)

- **必选测试**:
    - 所有主键需定义 `unique` 和 `not_null`。
    - 关键状态字段（如 `sync_status`）需定义 `accepted_values`。
- **业务验证**: 复杂逻辑需在 `dbt_project/tests/` 下编写 `Singular Tests`。
- **元数据**: 在 `schema.yml` 中描述关键列的业务含义（Business Glossary）。

## 6. 身份归因协议 (Identity Attribution)

- **自愈逻辑**: `int_golden_identity` 必须包含基于 SCD2 历史版本的字段回溯，确保即使当前部门缺失，也能找回“当时的历史部门”进行成本分摊。
- **溯源透明**: 归一化后的记录必须标注 `attribution_source`（如 "Direct Match", "History Fallback", "Manual Map"）。

## 7. 数据生命周期与清理 (Data Lifecycle)

### 7.1 软删除与存续性检查
- **僵尸数据过滤**: 所有 Marts 层模型必须基于 `mdm_systems_registry` 或拓扑表的存续性标志。
- **一致性**: 严禁在报表中展示已在源系统物理删除的“幽灵记录”，除非该记录被明确标注为 `is_historical_archive`。

### 7.2 主数据刷新规范
- **定向重置**: 主数据（组织/产品/项目）变更时，必须使用标准工具 `scripts/refresh_master_data.py` 进行定向重置，严禁手动 `TRUNCATE` 导致外键引用崩溃。

## 8. 测试分级与 CI 门禁 (Testing & CI/CD)

### 8.1 测试严重性 (Severity)
- **Error (阻断)**: 主键冲突、关键 ID 为空、数据类型溢出。必须中断 CI 流水线，禁止物化下游模型。
- **Warn (预警)**: 业务逻辑异常（如单次工时 > 24h）。允许执行完毕，但必须在大屏展示数据风险警告。

### 8.2 单元测试强制化
- 针对涉及 DORA MTTR 计算、资本化 ROI 逻辑的 `int_` 层模型，必须编写 `singular tests` 或使用模拟数据的 `unit tests` 覆盖边界场景。

## 9. 数据治理与 Schema 监控 (Governance)

### 9.1 Schema Drift 防御
- 核心 Source 必须配置 `freshness` 检查。
- 关键 Staging 模型应包含字段存续性审计，防止源端 API 结构变更导致数据静默丢失（Silent Failure）。

## 10. 高阶业务语义标准 (Advanced Semantics)

### 10.1 SCD2 冲突处理标准
- 身份与组织关联必须统一遵循：`优先查找 is_current=True` -> `失败则回溯最近历史版本` -> `仍失败则回填业务桩记录(Stub)` 的流水线逻辑。

---
**参考文档**: [contexts.md](../../contexts.md) | [lessons-learned.log](../lessons-learned.log)

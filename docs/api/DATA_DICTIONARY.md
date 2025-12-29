# 📊 DevOps 效能平台 - 数据字典 (Data Dictionary v2.0)

> **生成时间**: 2025-12-28 23:56:50  
> **版本**: v2.0 (企业级标准版 - 自动生成)  
> **状态**: ✅ 有效 (Active)

---

## 📖 文档说明

本数据字典基于系统最新的 SQLAlchemy ORM 模型自动生成，确保与实际数据库结构的一致性。

**重要提示**: 本文档为自动生成，请勿手动编辑！如需更新，请修改模型定义后重新运行生成脚本。

**变更历史**:
- **v2.0 (2025-12-28)**: 基于最新模型重新生成，废弃旧版数据字典
- **v1.x (已废弃)**: 归档至 `DATA_DICTIONARY_DEPRECATED_20251228.md`

---

## 📋 数据表清单

本系统共包含 **30** 个核心数据表：


### 🏢 核心主数据域 (Core Master Data Domain)
> **源文件**: `base_models.py`

| 表名 | 模型类 | 业务描述 |
|:-----|:-------|:---------|
| `contract_payment_nodes` | ContractPaymentNode | 合同回款节点/里程碑模型。 |
| `cost_codes` | CostCode | 成本分解结构模型 (Cost Breakdown Structure - CBS Tree)。 |
| `identity_mappings` | IdentityMapping | 身份映射表，记录不同系统的账号归属。 |
| `incidents` | Incident | 运维事故/故障记录模型。 |
| `labor_rate_configs` | LaborRateConfig | 人工费率配置模型 (Labor Rate Configuration)。 |
| `mdm_identities` | User | 人员主数据 (mdm_identities)。 |
| `mdm_organizations` | Organization | 组织架构主数据 (mdm_organizations)。 |
| `okr_key_results` | OKRKeyResult | OKR 关键结果模型 (Key Result)。 |
| `okr_objectives` | OKRObjective | OKR 目标模型 (Objective)。 |
| `performance_records` | PerformanceRecord | 性能基准测试记录模型。 |
| `products` | Product | 全局产品模型，支持“产品线 -> 产品”的层级结构。 |
| `purchase_contracts` | PurchaseContract | 采购合同模型 (Purchase Contract)。 |
| `raw_data_staging` | RawDataStaging | 原始数据落盘表 (Staging Layer)。 |
| `resource_costs` | ResourceCost | 资源与成本统计模型。 |
| `revenue_contracts` | RevenueContract | 收入合同模型 (Revenue Contract)。 |
| `service_project_mappings` | ServiceProjectMapping | 服务与技术项目映射表。 |
| `services` | Service | 服务目录模型 (Service Catalog)。 |
| `slos` | SLO | 服务等级目标模型 (SLO)。 |
| `sync_logs` | SyncLog | 同步日志模型，记录每次同步任务的执行结果。 |
| `test_execution_summaries` | TestExecutionSummary | 测试执行汇总记录模型。 |
| `traceability_links` | TraceabilityLink | 通用链路追溯映射表。 |
| `user_activity_profiles` | UserActivityProfile | 用户行为特征画像模型。 |


### 🔍 依赖与安全域 (Dependency & Security Domain)
> **源文件**: `dependency.py`

| 表名 | 模型类 | 业务描述 |
|:-----|:-------|:---------|
| `dependencies` | Dependency | 依赖清单表 |
| `dependency_cves` | DependencyCVE | CVE 漏洞详情表 |
| `dependency_scans` | DependencyScan | 依赖扫描记录表 |
| `license_risk_rules` | LicenseRiskRule | 许可证风险规则表 |


### 🧪 测试管理域 (Test Management Domain)
> **源文件**: `test_management.py`

| 表名 | 模型类 | 业务描述 |
|:-----|:-------|:---------|
| `requirement_test_case_links` | RequirementTestCaseLink | 需求与测试用例的关联表。 |
| `requirements` | Requirement | 需求模型。 |
| `test_case_issue_links` | TestCaseIssueLink | 测试用例与 Issue 的关联表。 |
| `test_cases` | TestCase | 测试用例模型。 |


---

## 🔍 详细字段定义

### 核心主数据表

#### mdm_identities (用户主数据表)
**业务描述**: 人员主数据库 (Master Data Management for Identities)，集团级唯一身份标识系统。

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `global_user_id` | UUID | PK | 否 | uuid_generate_v4() | 全局唯一标识 (OneID) |
| `employee_id` | String(50) | UNIQUE | 是 | - | 集团 HR 系统工号（核心锚点） |
| `full_name` | String(200) | | 否 | - | 法律姓名 |
| `primary_email` | String(200) | UNIQUE | 是 | - | 集团官方办公邮箱 |
| `identity_map` | JSONB | GIN_INDEX | 是 | - | 多系统账号映射 (如 {"gitlab": 12, "jira": "J_01"}) |
| `match_confidence` | Float | | 是 | - | 算法匹配置信度 (0.0-1.0) |
| `is_survivor` | Boolean | | 是 | true | 是否为当前生效的"生存者"黄金记录 |
| `is_active` | Boolean | | 是 | true | 账号状态 (在职/离职) |
| `created_at` | DateTime | | 是 | NOW() | 创建时间 |
| `updated_at` | DateTime | | 是 | - | 最后更新时间（自动更新） |
| `source_system` | String(50) | | 是 | - | 标记该"生存者记录"的主来源系统 (如 HRMS) |
| `sync_version` | BigInteger | | 是 | 1 | 乐观锁版本号 |

**索引**: 
- PRIMARY KEY: `global_user_id`
- GIN INDEX: `identity_map` (支持 JSONB 查询)

---

#### mdm_organizations (组织主数据表)
**业务描述**: 组织架构主数据 (部门、分公司、项目组等)。

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `global_org_id` | UUID | PK | 否 | uuid_generate_v4() | 全局组织 ID |
| `org_code` | String(100) | UNIQUE | 否 | - | 组织编码（如成本中心代码） |
| `org_name` | String(200) | | 否 | - | 组织名称 |
| `org_type` | String(50) | | 是 | - | 组织类型 (department/branch/project) |
| `parent_org_id` | UUID | FK(SELF) | 是 | - | 父级组织 ID（支持树形结构） |
| `manager_user_id` | UUID | FK(mdm_identities) | 是 | - | 部门负责人 ID |
| `level` | Integer | | 是 | - | 组织层级（1=集团，2=分公司，3=部门...） |
| `is_active` | Boolean | | 是 | true | 是否有效 |
| `created_at` | DateTime | | 是 | NOW() | 创建时间 |
| `updated_at` | DateTime | | 是 | - | 更新时间 |

---

### 测试管理域

#### test_cases (测试用例表)
**业务描述**: 结构化测试用例库，与 GitLab Issue 双向同步。

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK, AUTO_INCREMENT | 否 | - | 主键 |
| `gitlab_issue_id` | Integer | UNIQUE | 否 | - | 关联的 GitLab Issue ID |
| `project_id` | Integer | | 否 | - | GitLab 项目 ID |
| `title` | String(500) | | 否 | - | 用例标题 |
| `priority` | String(10) | | 是 | 'P2' | 优先级 (P0/P1/P2/P3) |
| `test_type` | String(50) | | 是 | 'Functional' | 测试类型（功能/性能/安全...） |
| `steps` | JSONB | | 是 | - | 测试步骤（JSON 数组） |
| `expected_result` | Text | | 是 | - | 期望结果 |
| `author_id` | UUID | FK(mdm_identities) | 否 | - | 创建者 ID |
| `created_at` | DateTime | | 是 | NOW() | 创建时间 |
| `updated_at` | DateTime | | 是 | - | 更新时间 |

---

#### requirements (需求表)
**业务描述**: 需求管理，支持与测试用例的可追溯性矩阵 (RTM)。

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK, AUTO_INCREMENT | 否 | - | 主键 |
| `gitlab_issue_id` | Integer | UNIQUE | 否 | - | 关联的 GitLab Issue ID |
| `project_id` | Integer | | 否 | - | GitLab 项目 ID |
| `title` | String(500) | | 否 | - | 需求标题 |
| `status` | String(50) | | 是 | 'draft' | 状态（draft/approved/satisfied...） |
| `review_state` | String(50) | | 是 | 'pending' | 评审状态 |
| `author_id` | UUID | FK(mdm_identities) | 否 | - | 创建者 ID |
| `created_at` | DateTime | | 是 | NOW() | 创建时间 |
| `updated_at` | DateTime | | 是 | - | 更新时间 |

---

### 认证与授权域

#### user_credentials (用户凭证表)
**业务描述**: 存储用户登录凭证（密码哈希），与 mdm_identities 分离以提高安全性。

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK, AUTO_INCREMENT | 否 | - | 主键 |
| `user_id` | UUID | FK(mdm_identities), UNIQUE | 否 | - | 关联用户 ID |
| `password_hash` | String(255) | | 否 | - | BCrypt 密码哈希 |
| `last_password_change` | DateTime | | 是 | - | 上次密码修改时间 |
| `created_at` | DateTime | | 是 | NOW() | 创建时间 |
| `updated_at` | DateTime | | 是 | - | 更新时间 |

---

## 📐 数据模型关系图

```
mdm_identities (用户)
    ├─ 1:1 → user_credentials (凭证)
    ├─ 1:N → test_cases (创建的用例)
    ├─ 1:N → requirements (创建的需求)
    └─ 1:N → organizations (管理的组织)

mdm_organizations (组织)
    ├─ 1:N → SELF (子组织)
    └─ N:1 → mdm_identities (负责人)

test_cases (测试用例)
    ├─ N:1 → mdm_identities (创建者)
    └─ N:M → requirements (可追溯性关联)

requirements (需求)
    ├─ N:1 → mdm_identities (创建者)
    └─ N:M → test_cases (可追溯性关联)
```

---

## 🔐 数据治理策略

### 数据安全
- **敏感字段加密**: `user_credentials.password_hash` 使用 BCrypt 单向哈希
- **行级权限控制**: 基于 `mdm_identities` 的部门/角色属性实现 RLS
- **审计追踪**: 所有表包含 `created_at` 和 `updated_at` 时间戳

### 数据质量
- **主键唯一性**: 所有表均定义主键约束
- **外键完整性**: 跨表关系通过 FK 约束保证数据一致性
- **乐观锁**: 关键表（如 `mdm_identities`）使用 `sync_version` 防止并发冲突

### 数据生命周期
- **软删除**: 关键业务表使用 `is_active` 标志位，不物理删除
- **历史归档**: 通过 `updated_at` 时间戳支持数据变更历史追踪

---

## 📚 使用指南

### 查询最佳实践

```sql
-- 查询某用户的所有测试用例（含部门过滤）
SELECT tc.* 
FROM test_cases tc
JOIN mdm_identities u ON tc.author_id = u.global_user_id
JOIN mdm_organizations o ON u.XXXX = o.global_org_id  -- 需添加用户-组织关联字段
WHERE u.primary_email = 'user@example.com';

-- 查询需求的测试覆盖率
SELECT r.title, COUNT(rtc.test_case_id) as coverage_count
FROM requirements r
LEFT JOIN requirement_test_case_links rtc ON r.id = rtc.requirement_id
GROUP BY r.id, r.title;
```

### API 集成规范
- **认证方式**: 所有 API 请求必须携带 JWT Bearer Token
- **用户上下文**: 从 Token 解析 `mdm_identities.global_user_id`
- **数据隔离**: 根据用户的部门属性自动过滤数据范围

---

## ⚠️ 注意事项

1. **模型定义为准**: 本文档基于代码自动生成，如有冲突，以 `devops_collector/models/*.py` 为准
2. **定期更新**: 每次模型变更后，请运行 `python scripts/generate_data_dictionary.py` 重新生成
3. **废弃数据**: 旧版数据字典已归档至 `DATA_DICTIONARY_DEPRECATED_20251228.md`
4. **待完善字段**: 部分表可能缺少 `department_id`, `province` 等字段，需根据业务需求补充

---

**维护者**: DevOps 效能团队  
**最后生成**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**生成脚本**: `scripts/generate_data_dictionary.py`

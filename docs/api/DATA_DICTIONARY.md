# DevOps 效能平台 - 数据字典 (Data Dictionary)

> **生成时间**: 2026-01-17 00:13:44  
> **版本**: v2.1 (企业级标准版)  
> **状态**: 有效 (Active)

---

## 文档说明

本数据字典基于系统最新的 SQLAlchemy ORM 模型自动生成，确保与实际数据库结构的一致性。

### 文档结构
- **表名**: 数据库表的物理名称
- **模型类**: 对应的 Python ORM 模型类名
- **业务描述**: 从模型 Docstring 提取的业务用途说明
- **字段定义**: 包含字段名、类型、约束、可空性、默认值和业务说明
- **关系映射**: 表间的 ORM 关系（一对多、多对一等）

---

## 数据表清单

本系统共包含 **73 个数据表**，分为以下几个业务域：


### 核心主数据域 (Core Master Data)
- `mdm_calendar` - Calendar
- `mdm_company` - Company
- `mdm_compliance_issues` - ComplianceIssue
- `mdm_contract_payment_nodes` - ContractPaymentNode
- `mdm_cost_codes` - CostCode
- `mdm_entity_topology` - EntityTopology
- `mdm_epic` - EpicMaster
- `mdm_identities` - User
- `mdm_identity_mappings` - IdentityMapping
- `mdm_incidents` - Incident
- `mdm_labor_rate_config` - LaborRateConfig
- `mdm_locations` - Location
- `mdm_metric_definitions` - MetricDefinition
- `mdm_okr_key_results` - OKRKeyResult
- `mdm_okr_objectives` - OKRObjective
- `mdm_organizations` - Organization
- `mdm_product` - Product
- `mdm_projects` - ProjectMaster
- `mdm_purchase_contracts` - PurchaseContract
- `mdm_rel_project_product` - ProjectProductRelation
- `mdm_revenue_contracts` - RevenueContract
- `mdm_service_project_mapping` - ServiceProjectMapping
- `mdm_services` - Service
- `mdm_slo_definitions` - SLO
- `mdm_systems_registry` - SystemRegistry
- `mdm_traceability_links` - TraceabilityLink
- `mdm_vendor` - Vendor
- `stg_mdm_resource_costs` - ResourceCost

### 测试管理域 (Test Management)
- `fct_test_execution_summary` - TestExecutionSummary
- `gtm_requirements` - GTMRequirement
- `gtm_test_case_issue_links` - GTMTestCaseIssueLink
- `gtm_test_cases` - GTMTestCase
- `gtm_test_execution_records` - GTMTestExecutionRecord

### GitLab 集成域 (GitLab Integration)
- `gitlab_branches` - GitLabBranch
- `gitlab_commits` - GitLabCommit
- `gitlab_deployments` - GitLabDeployment
- `gitlab_group_members` - GitLabGroupMember
- `gitlab_groups` - GitLabGroup
- `gitlab_issues` - GitLabIssue
- `gitlab_merge_requests` - GitLabMergeRequest
- `gitlab_milestones` - GitLabMilestone
- `gitlab_notes` - GitLabNote
- `gitlab_packages` - GitLabPackage
- `gitlab_pipelines` - GitLabPipeline
- `gitlab_project_members` - GitLabProjectMember
- `gitlab_projects` - GitLabProject
- `gitlab_releases` - GitLabRelease
- `gitlab_tags` - GitLabTag

### 认证与授权域 (Authentication & Authorization)
- `sys_user_credentials` - UserCredential
- `sys_user_oauth_tokens` - UserOAuthToken

### 其他辅助域 (Other Supporting Tables)
- `commit_metrics` - CommitMetrics
- `daily_dev_stats` - DailyDevStats
- `dependencies` - Dependency
- `dependency_cves` - DependencyCVE
- `dependency_scans` - DependencyScan
- `fct_performance_records` - PerformanceRecord
- `fct_user_activity_profiles` - UserActivityProfile
- `jira_boards` - JiraBoard
- `jira_issues` - JiraIssue
- `jira_projects` - JiraProject
- `jira_sprints` - JiraSprint
- `license_risk_rules` - LicenseRiskRule
- `rbac_permissions` - Permission
- `rbac_roles` - Role
- `sonar_issues` - SonarIssue
- `sonar_measures` - SonarMeasure
- `sonar_projects` - SonarProject
- `stg_raw_data` - RawDataStaging
- `sys_role_permissions` - RolePermission
- `sys_sync_logs` - SyncLog
- `sys_team_members` - TeamMember
- `sys_teams` - Team
- `sys_user_roles` - UserRole

---

## 核心主数据域

### Calendar (`mdm_calendar`)

**业务描述**: 公共日历/节假日参考表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `date_day` | DATE | UNIQUE, INDEX | 否 | - | - |
| `year_number` | Integer | INDEX | 是 | - | - |
| `month_number` | Integer | - | 是 | - | - |
| `quarter_number` | Integer | - | 是 | - | - |
| `day_of_week` | Integer | - | 是 | - | - |
| `is_workday` | Boolean | - | 是 | True | - |
| `is_holiday` | Boolean | - | 是 | False | - |
| `holiday_name` | String(100) | - | 是 | - | - |
| `fiscal_year` | String(20) | - | 是 | - | - |
| `fiscal_quarter` | String(20) | - | 是 | - | - |
| `week_of_year` | Integer | - | 是 | - | - |
| `season_tag` | String(20) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### Company (`mdm_company`)

**业务描述**: 公司实体参考表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `company_id` | String(50) | PK | 否 | - | - |

---

### ComplianceIssue (`mdm_compliance_issues`)

**业务描述**: 合规风险与审计问题记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `issue_type` | String(50) | - | 是 | - | - |
| `severity` | String(20) | - | 是 | - | - |
| `entity_id` | String(100) | - | 是 | - | - |
| `status` | String(20) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `metadata_payload` | JSON | - | 是 | - | - |

---

### ContractPaymentNode (`mdm_contract_payment_nodes`)

**业务描述**: 合同付款节点/收款计划记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `contract_id` | Integer | FK | 否 | - | - |
| `node_name` | String(200) | - | 否 | - | - |
| `billing_percentage` | Numeric | - | 是 | - | - |
| `billing_amount` | Numeric | - | 是 | - | - |
| `linked_system` | String(50) | - | 是 | - | - |
| `linked_milestone_id` | Integer | - | 是 | - | - |
| `is_achieved` | Boolean | - | 是 | False | - |
| `achieved_at` | DateTime | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **contract**: many-to-one → `RevenueContract`

---

### CostCode (`mdm_cost_codes`)

**业务描述**: 成本科目 (CBS) 模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `code` | String(50) | UNIQUE, INDEX | 否 | - | - |
| `name` | String(200) | - | 否 | - | - |
| `category` | String(50) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `parent_id` | Integer | FK | 是 | - | - |
| `default_capex_opex` | String(10) | - | 是 | - | - |
| `is_active` | Boolean | - | 是 | True | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **parent**: many-to-one → `CostCode`
- **children**: one-to-many → `CostCode`

---

### EntityTopology (`mdm_entity_topology`)

**业务描述**: 实体-资源映射表 (Infrastructure Mapping). 将逻辑上的业务服务 (Service) 绑定到物理上的基础设施资源 (GitLab Repo, Sonar Project, Jenkins Job)。 它是连接 "业务架构" (Service) 与 "工具设施" (SystemRegistry) 的胶水层。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `service_id` | Integer | FK, INDEX | 否 | - | - |
| `system_code` | String(50) | FK | 否 | - | - |
| `external_resource_id` | String(100) | - | 否 | - | - |
| `element_type` | String(50) | - | 是 | source-code | - |
| `is_active` | Boolean | - | 是 | True | - |
| `last_verified_at` | DateTime | - | 是 | - | - |
| `meta_info` | JSON | - | 是 | - | - |
| `is_current` | Boolean | - | 是 | True | - |
| `sync_version` | Integer | - | 是 | 1 | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **service**: many-to-one → `Service`
- **target_system**: many-to-one → `SystemRegistry`

---

### EpicMaster (`mdm_epic`)

**业务描述**: 跨团队/长期史诗需求 (Epic) 主数据。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |

---

### User (`mdm_identities`)

**业务描述**: 全局用户映射表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `global_user_id` | UUID | PK | 否 | <function uuid4 at 0x00000235BE80D8A0> | - |
| `employee_id` | String(50) | UNIQUE, INDEX | 是 | - | - |
| `username` | String(100) | - | 是 | - | - |
| `full_name` | String(200) | - | 是 | - | - |
| `primary_email` | String(255) | UNIQUE, INDEX | 是 | - | - |
| `department_id` | String(100) | FK | 是 | - | - |
| `is_active` | Boolean | - | 是 | True | - |
| `is_survivor` | Boolean | - | 是 | False | - |
| `total_eloc` | Numeric | - | 是 | 0.0 | - |
| `eloc_rank` | Integer | - | 是 | 0 | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | <function SCDMixin.<lambda> at 0x00000235BE8327A0> | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **department**: many-to-one → `Organization`
- **managed_organizations**: one-to-many → `Organization`
- **identities**: one-to-many → `IdentityMapping`
- **roles**: one-to-many → `Role`
- **test_cases**: one-to-many → `GTMTestCase`
- **requirements**: one-to-many → `GTMRequirement`
- **managed_products_as_pm**: one-to-many → `Product`
- **project_memberships**: one-to-many → `GitLabProjectMember`
- **team_memberships**: one-to-many → `TeamMember`
- **credential**: many-to-one → `UserCredential`

---

### IdentityMapping (`mdm_identity_mappings`)

**业务描述**: 外部身份映射表，连接 MDM 用户与第三方系统账号。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `global_user_id` | UUID | FK, INDEX | 是 | - | - |
| `source_system` | String(50) | INDEX | 否 | - | - |
| `external_user_id` | String(100) | - | 否 | - | - |
| `external_username` | String(100) | - | 是 | - | - |
| `external_email` | String(100) | - | 是 | - | - |
| `mapping_status` | String(20) | - | 是 | VERIFIED | - |
| `confidence_score` | Numeric | - | 是 | 1.0 | - |
| `last_active_at` | DateTime | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **user**: many-to-one → `User`

---

### Incident (`mdm_incidents`)

**业务描述**: 线上事故/线上问题记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |

---

### LaborRateConfig (`mdm_labor_rate_config`)

**业务描述**: 人工标准费率配置表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `job_title_level` | String(50) | - | 否 | - | - |
| `daily_rate` | Numeric | - | 否 | - | - |
| `hourly_rate` | Numeric | - | 是 | - | - |
| `currency` | String(10) | - | 是 | CNY | - |
| `effective_date` | DateTime | - | 是 | - | - |
| `is_active` | Boolean | - | 是 | True | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### Location (`mdm_locations`)

**业务描述**: 地理位置或机房位置参考表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `location_id` | String(50) | UNIQUE, INDEX | 是 | - | - |
| `location_name` | String(200) | - | 否 | - | - |
| `short_name` | String(50) | - | 是 | - | - |
| `location_type` | String(50) | - | 是 | - | - |
| `parent_id` | String(50) | - | 是 | - | - |
| `region` | String(50) | - | 是 | - | - |
| `is_active` | Boolean | - | 是 | True | - |
| `manager_user_id` | UUID | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### MetricDefinition (`mdm_metric_definitions`)

**业务描述**: 指标语义定义表 (mdm_metric_definitions)。 这是 "指标字典" 的核心，确保全集团计算逻辑一致 (Single Source of Truth)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `metric_code` | String(100) | PK | 否 | - | - |
| `metric_name` | String(200) | - | 否 | - | - |
| `domain` | String(50) | - | 否 | - | - |
| `metric_type` | String(50) | - | 是 | - | - |
| `calculation_logic` | Text | - | 是 | - | - |
| `unit` | String(50) | - | 是 | - | - |
| `aggregate_type` | String(20) | - | 是 | - | - |
| `source_model` | String(200) | - | 是 | - | - |
| `dimension_scope` | JSON | - | 是 | - | - |
| `is_standard` | Boolean | - | 是 | True | - |
| `business_owner_id` | UUID | FK | 是 | - | - |
| `time_grain` | String(50) | - | 是 | - | - |
| `update_cycle` | String(50) | - | 是 | - | - |
| `status` | String(50) | - | 是 | RELEASED | - |
| `is_active` | Boolean | - | 是 | True | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **business_owner**: many-to-one → `User`

---

### OKRKeyResult (`mdm_okr_key_results`)

**业务描述**: OKR 关键结果 (KR) 定义表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `objective_id` | Integer | FK | 否 | - | - |
| `title` | String(255) | - | 否 | - | - |
| `target_value` | Numeric | - | 否 | - | - |
| `current_value` | Numeric | - | 是 | 0.0 | - |
| `unit` | String(20) | - | 是 | - | - |
| `weight` | Numeric | - | 是 | 1.0 | - |
| `owner_id` | UUID | FK | 是 | - | - |
| `progress` | Numeric | - | 是 | 0.0 | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **objective**: many-to-one → `OKRObjective`
- **owner**: many-to-one → `User`

---

### OKRObjective (`mdm_okr_objectives`)

**业务描述**: OKR 目标定义表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `objective_id` | String(50) | UNIQUE, INDEX | 是 | - | - |
| `title` | String(255) | - | 否 | - | - |
| `description` | Text | - | 是 | - | - |
| `period` | String(20) | INDEX | 是 | - | - |
| `owner_id` | UUID | FK | 是 | - | - |
| `org_id` | String(100) | FK | 是 | - | - |
| `status` | String(20) | - | 是 | ACTIVE | - |
| `progress` | Numeric | - | 是 | 0.0 | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **owner**: many-to-one → `User`
- **organization**: many-to-one → `Organization`
- **key_results**: one-to-many → `OKRKeyResult`

---

### Organization (`mdm_organizations`)

**业务描述**: 组织架构表，支持 SCD Type 2 生命周期管理。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `org_id` | String(100) | UNIQUE, INDEX | 否 | - | - |
| `org_name` | String(200) | - | 否 | - | - |
| `org_level` | Integer | - | 是 | 1 | - |
| `parent_org_id` | String(100) | FK | 是 | - | - |
| `manager_user_id` | UUID | FK | 是 | - | - |
| `is_active` | Boolean | - | 是 | True | - |
| `cost_center` | String(100) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | <function SCDMixin.<lambda> at 0x00000235BE8327A0> | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **parent**: many-to-one → `Organization`
- **manager**: many-to-one → `User`
- **users**: one-to-many → `User`
- **products**: one-to-many → `Product`
- **gitlab_projects**: one-to-many → `GitLabProject`
- **children**: one-to-many → `Organization`

---

### Product (`mdm_product`)

**业务描述**: 产品主数据表 (mdm_product)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `product_id` | String(100) | PK | 否 | - | - |
| `product_code` | String(25) | INDEX | 否 | - | - |
| `product_name` | String(255) | - | 否 | - | - |
| `product_description` | Text | - | 否 | - | - |
| `category` | String(100) | - | 是 | - | - |
| `version_schema` | String(50) | - | 否 | - | - |
| `specification` | JSON | - | 是 | - | - |
| `runtime_env` | JSON | - | 是 | - | - |
| `checksum` | String(255) | - | 是 | - | - |
| `lifecycle_status` | String(50) | - | 是 | Active | - |
| `repo_url` | String(255) | - | 是 | - | - |
| `artifact_path` | String(255) | - | 是 | - | - |
| `owner_team_id` | String(100) | FK | 是 | - | - |
| `product_manager_id` | UUID | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **owner_team**: many-to-one → `Organization`
- **product_manager**: many-to-one → `User`
- **project_relations**: one-to-many → `ProjectProductRelation`

---

### ProjectMaster (`mdm_projects`)

**业务描述**: 项目全生命周期主数据 (mdm_projects)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `project_id` | String(100) | PK | 否 | - | - |
| `project_name` | String(200) | - | 否 | - | - |
| `project_type` | String(50) | - | 是 | - | - |
| `status` | String(50) | - | 是 | PLAN | - |
| `is_active` | Boolean | - | 是 | True | - |
| `pm_user_id` | UUID | FK | 是 | - | - |
| `org_id` | String(100) | FK | 是 | - | - |
| `plan_start_date` | DATE | - | 是 | - | - |
| `plan_end_date` | DATE | - | 是 | - | - |
| `actual_start_at` | DateTime | - | 是 | - | - |
| `actual_end_at` | DateTime | - | 是 | - | - |
| `external_id` | String(100) | UNIQUE | 是 | - | - |
| `system_code` | String(50) | FK | 是 | - | - |
| `budget_code` | String(100) | - | 是 | - | - |
| `budget_type` | String(50) | - | 是 | - | - |
| `lead_repo_id` | Integer | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | <function SCDMixin.<lambda> at 0x00000235BE8327A0> | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **organization**: many-to-one → `Organization`
- **project_manager**: many-to-one → `User`
- **source_system**: many-to-one → `SystemRegistry`
- **gitlab_repos**: one-to-many → `GitLabProject`
- **product_relations**: one-to-many → `ProjectProductRelation`

---

### PurchaseContract (`mdm_purchase_contracts`)

**业务描述**: 采购/支出合同主数据。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `contract_no` | String(100) | UNIQUE, INDEX | 否 | - | - |
| `title` | String(255) | - | 是 | - | - |
| `vendor_name` | String(255) | - | 是 | - | - |
| `vendor_id` | String(100) | - | 是 | - | - |
| `total_amount` | Numeric | - | 是 | 0.0 | - |
| `currency` | String(10) | - | 是 | CNY | - |
| `start_date` | DATE | - | 是 | - | - |
| `end_date` | DATE | - | 是 | - | - |
| `cost_code_id` | Integer | FK | 是 | - | - |
| `capex_opex_flag` | String(10) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **cost_code**: many-to-one → `CostCode`

---

### ProjectProductRelation (`mdm_rel_project_product`)

**业务描述**: 项目与产品的关联权重表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | String(100) | FK, INDEX | 否 | - | - |
| `org_id` | String(100) | INDEX | 否 | - | - |
| `product_id` | String(100) | FK, INDEX | 否 | - | - |
| `relation_type` | String(50) | - | 是 | PRIMARY | - |
| `allocation_ratio` | Numeric | - | 是 | 1.0 | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `ProjectMaster`
- **product**: many-to-one → `Product`

---

### RevenueContract (`mdm_revenue_contracts`)

**业务描述**: 销售/收入合同主数据表格。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `contract_no` | String(100) | UNIQUE, INDEX | 否 | - | - |
| `title` | String(255) | - | 是 | - | - |
| `client_name` | String(255) | - | 是 | - | - |
| `total_value` | Numeric | - | 是 | 0.0 | - |
| `currency` | String(10) | - | 是 | CNY | - |
| `sign_date` | DATE | - | 是 | - | - |
| `product_id` | String(100) | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **product**: many-to-one → `Product`
- **payment_nodes**: one-to-many → `ContractPaymentNode`

---

### ServiceProjectMapping (`mdm_service_project_mapping`)

**业务描述**: 服务与工程项目的多对多关联映射表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `service_id` | Integer | FK | 否 | - | - |
| `source` | String(50) | - | 是 | - | - |
| `project_id` | Integer | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **service**: many-to-one → `Service`

---

### Service (`mdm_services`)

**业务描述**: 服务/组件目录表 (Extended with Backstage Component Model).

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `name` | String(200) | - | 否 | - | - |
| `tier` | String(20) | - | 是 | - | - |
| `org_id` | String(100) | FK | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `system_id` | Integer | FK | 是 | - | - |
| `lifecycle` | String(20) | - | 是 | production | - |
| `component_type` | String(20) | - | 是 | service | - |
| `tags` | JSON | - | 是 | - | - |
| `links` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **system**: many-to-one → `BusinessSystem`
- **organization**: many-to-one → `Organization`
- **costs**: one-to-many → `ResourceCost`
- **slos**: one-to-many → `SLO`
- **project_mappings**: one-to-many → `ServiceProjectMapping`
- **resources**: one-to-many → `EntityTopology`

---

### SLO (`mdm_slo_definitions`)

**业务描述**: SLO (服务水平目标) 定义表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `service_id` | Integer | FK | 否 | - | - |
| `name` | String(100) | - | 否 | - | - |
| `indicator_type` | String(50) | - | 是 | - | - |
| `target_value` | Numeric | - | 是 | - | - |
| `metric_unit` | String(20) | - | 是 | - | - |
| `time_window` | String(20) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **service**: many-to-one → `Service`

---

### SystemRegistry (`mdm_systems_registry`)

**业务描述**: 三方系统注册表，记录对接的所有外部系统 (GitLab, Jira, Sonar 等)。 作为数据源治理注册中心，定义了连接方式、同步策略及数据治理属性。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `system_code` | String(50) | PK | 否 | - | - |
| `system_name` | String(100) | - | 否 | - | - |
| `system_type` | String(50) | - | 是 | - | - |
| `base_url` | String(255) | - | 是 | - | - |
| `api_version` | String(20) | - | 是 | - | - |
| `auth_type` | String(50) | - | 是 | - | - |
| `sync_method` | String(50) | - | 是 | - | - |
| `update_cycle` | String(50) | - | 是 | - | - |
| `data_sensitivity` | String(20) | - | 是 | - | - |
| `sla_level` | String(20) | - | 是 | - | - |
| `technical_owner_id` | UUID | FK | 是 | - | - |
| `is_active` | Boolean | - | 是 | True | - |
| `last_heartbeat` | DateTime | - | 是 | - | - |
| `remarks` | Text | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **technical_owner**: many-to-one → `User`
- **projects**: one-to-many → `ProjectMaster`

---

### TraceabilityLink (`mdm_traceability_links`)

**业务描述**: 跨系统追溯链路表，连接需求与代码、测试与发布。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `source_system` | String(50) | - | 是 | - | - |
| `source_type` | String(50) | - | 是 | - | - |
| `source_id` | String(100) | - | 是 | - | - |
| `target_system` | String(50) | - | 是 | - | - |
| `target_type` | String(50) | - | 是 | - | - |
| `target_id` | String(100) | - | 是 | - | - |
| `link_type` | String(50) | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

---

### Vendor (`mdm_vendor`)

**业务描述**: 外部供应商参考表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `vendor_code` | String(50) | PK | 否 | - | - |

---

### ResourceCost (`stg_mdm_resource_costs`)

**业务描述**: 资源成本记录明细表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `service_id` | Integer | FK | 是 | - | - |
| `cost_code_id` | Integer | FK | 是 | - | - |
| `purchase_contract_id` | Integer | FK | 是 | - | - |
| `period` | String(20) | INDEX | 是 | - | - |
| `amount` | Numeric | - | 是 | 0.0 | - |
| `currency` | String(10) | - | 是 | CNY | - |
| `cost_type` | String(50) | - | 是 | - | - |
| `cost_item` | String(200) | - | 是 | - | - |
| `vendor_name` | String(200) | - | 是 | - | - |
| `capex_opex_flag` | String(10) | - | 是 | - | - |
| `source_system` | String(100) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **service**: many-to-one → `Service`
- **cost_code**: many-to-one → `CostCode`
- **purchase_contract**: many-to-one → `PurchaseContract`

---

## 测试管理域

### TestExecutionSummary (`fct_test_execution_summary`)

**业务描述**: 测试执行汇总记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |

---

### GTMRequirement (`gtm_requirements`)

**业务描述**: GitLab 需求模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `author_id` | UUID | FK | 否 | - | - |
| `iid` | Integer | - | 否 | - | - |
| `title` | String(255) | - | 否 | - | - |
| `description` | Text | - | 是 | - | - |
| `state` | String(20) | - | 是 | opened | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **author**: many-to-one → `User`
- **project**: many-to-one → `GitLabProject`
- **test_cases**: one-to-many → `GTMTestCase`

---

### GTMTestCaseIssueLink (`gtm_test_case_issue_links`)

**业务描述**: 测试用例与 Issue 的关联表 (gtm_test_case_issue_links)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `test_case_id` | Integer | FK | 否 | - | - |
| `issue_id` | Integer | FK | 否 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### GTMTestCase (`gtm_test_cases`)

**业务描述**: GitLab 测试用例模型。 存储测试用例的结构化信息，包括标题、描述（预置条件）和详细的执行步骤。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `author_id` | UUID | FK | 否 | - | - |
| `iid` | Integer | - | 否 | - | - |
| `title` | String(255) | - | 否 | - | - |
| `priority` | String(20) | - | 是 | - | - |
| `test_type` | String(50) | - | 是 | - | - |
| `pre_conditions` | Text | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `test_steps` | JSON | - | 是 | [] | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **author**: many-to-one → `User`
- **project**: many-to-one → `GitLabProject`
- **linked_issues**: one-to-many → `GitLabIssue`
- **associated_requirements**: one-to-many → `GTMRequirement`
- **execution_records**: one-to-many → `GTMTestExecutionRecord`

---

### GTMTestExecutionRecord (`gtm_test_execution_records`)

**业务描述**: 测试执行完整审计记录模型 (gtm_test_execution_records)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `test_case_iid` | Integer | INDEX | 否 | - | - |
| `result` | String(20) | - | 否 | - | - |
| `executed_at` | DateTime | - | 是 | now() | - |
| `executor_name` | String(100) | - | 是 | - | - |
| `executor_uid` | UUID | - | 是 | - | - |
| `comment` | Text | - | 是 | - | - |
| `pipeline_id` | Integer | - | 是 | - | - |
| `environment` | String(50) | - | 是 | Default | - |
| `title` | String(255) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`

---

## GitLab 集成域

### GitLabBranch (`gitlab_branches`)

**业务描述**: 分支模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `name` | String | - | 是 | - | - |
| `last_commit_sha` | String | - | 是 | - | - |
| `last_commit_date` | DateTime | - | 是 | - | - |
| `last_committer_name` | String | - | 是 | - | - |
| `is_merged` | Boolean | - | 是 | - | - |
| `is_protected` | Boolean | - | 是 | - | - |
| `is_default` | Boolean | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`

---

### GitLabCommit (`gitlab_commits`)

**业务描述**: GitLab 提交模型。 记录 Git 仓库的原子变更，并关联到项目和作者。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | String | PK | 否 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `short_id` | String | - | 是 | - | - |
| `title` | String | - | 是 | - | - |
| `author_name` | String | - | 是 | - | - |
| `author_email` | String | - | 是 | - | - |
| `message` | Text | - | 是 | - | - |
| `authored_date` | DateTime | - | 是 | - | - |
| `committed_date` | DateTime | - | 是 | - | - |
| `additions` | Integer | - | 是 | 0 | - |
| `deletions` | Integer | - | 是 | 0 | - |
| `total` | Integer | - | 是 | 0 | - |
| `is_off_hours` | Boolean | - | 是 | False | - |
| `linked_issue_ids` | JSON | - | 是 | - | - |
| `issue_source` | String(50) | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `gitlab_user_id` | UUID | FK | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`
- **author**: many-to-one → `User`

---

### GitLabDeployment (`gitlab_deployments`)

**业务描述**: 部署记录模型。 记录代码被部署到不同环境的执行结果及其追踪 SHA。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `iid` | Integer | - | 是 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `status` | String | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `ref` | String | - | 是 | - | - |
| `sha` | String | - | 是 | - | - |
| `environment` | String | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`

---

### GitLabGroupMember (`gitlab_group_members`)

**业务描述**: GitLab 群组成员模型。 维护用户与群组之间的多对多关联及权限信息。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `group_id` | Integer | FK | 是 | - | - |
| `user_id` | UUID | FK | 是 | - | - |
| `gitlab_uid` | Integer | - | 是 | - | - |
| `access_level` | Integer | - | 是 | - | - |
| `state` | String(20) | - | 是 | - | - |
| `joined_at` | DateTime | - | 是 | - | - |
| `expires_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **group**: many-to-one → `GitLabGroup`
- **user**: many-to-one → `User`

---

### GitLabGroup (`gitlab_groups`)

**业务描述**: GitLab 群组模型。 代表 GitLab 中的顶级或子群组，支持树形嵌套结构。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `name` | String(255) | - | 是 | - | - |
| `path` | String(255) | - | 是 | - | - |
| `full_path` | String(500) | UNIQUE | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `parent_id` | Integer | FK | 是 | - | - |
| `visibility` | String(20) | - | 是 | - | - |
| `avatar_url` | String(500) | - | 是 | - | - |
| `web_url` | String(500) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **children**: one-to-many → `GitLabGroup`
- **projects**: one-to-many → `GitLabProject`
- **members**: one-to-many → `GitLabGroupMember`
- **parent**: many-to-one → `GitLabGroup`

---

### GitLabIssue (`gitlab_issues`)

**业务描述**: 议题 (Issue) 模型。 代表项目中的任务、缺陷或需求。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `iid` | Integer | - | 是 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `title` | String | - | 是 | - | - |
| `description` | String | - | 是 | - | - |
| `state` | String | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `closed_at` | DateTime | - | 是 | - | - |
| `time_estimate` | Integer | - | 是 | - | - |
| `total_time_spent` | Integer | - | 是 | - | - |
| `weight` | Integer | - | 是 | - | - |
| `work_item_type` | String(50) | - | 是 | - | - |
| `ai_category` | String(50) | - | 是 | - | - |
| `ai_summary` | Text | - | 是 | - | - |
| `ai_confidence` | Numeric | - | 是 | - | - |
| `labels` | JSON | - | 是 | - | - |
| `first_response_at` | DateTime | - | 是 | - | - |
| `milestone_id` | Integer | FK | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `author_id` | UUID | FK | 是 | - | - |

#### 关系映射

- **author**: many-to-one → `User`
- **project**: many-to-one → `GitLabProject`
- **events**: one-to-many → `GitLabIssueEvent`
- **transitions**: one-to-many → `GitLabIssueStateTransition`
- **blockages**: one-to-many → `GitLabBlockage`
- **milestone**: many-to-one → `GitLabMilestone`
- **merge_requests**: one-to-many → `GitLabMergeRequest`
- **associated_test_cases**: one-to-many → `GTMTestCase`

---

### GitLabMergeRequest (`gitlab_merge_requests`)

**业务描述**: 合并请求 (MR) 模型。 存储代码合并请求的核心数据及其在 DevOps 生命周期中的协作元数据。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `iid` | Integer | - | 是 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `title` | String | - | 是 | - | - |
| `description` | String | - | 是 | - | - |
| `state` | String | - | 是 | - | - |
| `author_username` | String | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `merged_at` | DateTime | - | 是 | - | - |
| `closed_at` | DateTime | - | 是 | - | - |
| `reviewers` | JSON | - | 是 | - | - |
| `changes_count` | String | - | 是 | - | - |
| `diff_refs` | JSON | - | 是 | - | - |
| `merge_commit_sha` | String | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `external_issue_id` | String(100) | - | 是 | - | - |
| `issue_source` | String(50) | - | 是 | - | - |
| `first_response_at` | DateTime | - | 是 | - | - |
| `review_cycles` | Integer | - | 是 | 1 | - |
| `human_comment_count` | Integer | - | 是 | 0 | - |
| `approval_count` | Integer | - | 是 | 0 | - |
| `review_time_total` | BigInteger | - | 是 | - | - |
| `quality_gate_status` | String(20) | - | 是 | - | - |
| `ai_category` | String(50) | - | 是 | - | - |
| `ai_summary` | Text | - | 是 | - | - |
| `ai_confidence` | Numeric | - | 是 | - | - |
| `author_id` | UUID | FK | 是 | - | - |

#### 关系映射

- **deployments**: one-to-many → `GitLabDeployment`
- **author**: many-to-one → `User`
- **project**: many-to-one → `GitLabProject`

---

### GitLabMilestone (`gitlab_milestones`)

**业务描述**: 里程碑模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `iid` | Integer | - | 是 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `title` | String | - | 是 | - | - |
| `description` | String | - | 是 | - | - |
| `state` | String | - | 是 | - | - |
| `due_date` | DateTime | - | 是 | - | - |
| `start_date` | DateTime | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`
- **releases**: one-to-many → `GitLabRelease`
- **issues**: one-to-many → `GitLabIssue`

---

### GitLabNote (`gitlab_notes`)

**业务描述**: 评论/笔记模型。 存储 Issue、MR 等对象下的讨论内容和系统通知。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `noteable_type` | String | - | 是 | - | - |
| `noteable_iid` | Integer | - | 是 | - | - |
| `body` | String | - | 是 | - | - |
| `author_id` | UUID | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `system` | Boolean | - | 是 | - | - |
| `resolvable` | Boolean | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`

---

### GitLabPackage (`gitlab_packages`)

**业务描述**: GitLab 制品库包模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `name` | String(255) | - | 否 | - | - |
| `version` | String(100) | - | 是 | - | - |
| `package_type` | String(50) | - | 是 | - | - |
| `status` | String(50) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `web_url` | String(500) | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`
- **files**: one-to-many → `GitLabPackageFile`

---

### GitLabPipeline (`gitlab_pipelines`)

**业务描述**: 流水线 (CI/CD Pipeline) 模型。 记录 CI/CD 执行的结果、时长和覆盖率等工程效能核心指标。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `status` | String | - | 是 | - | - |
| `ref` | String | - | 是 | - | - |
| `sha` | String | - | 是 | - | - |
| `source` | String | - | 是 | - | - |
| `duration` | Integer | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `coverage` | String | - | 是 | - | - |
| `failure_reason` | String | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`

---

### GitLabProjectMember (`gitlab_project_members`)

**业务描述**: GitLab 项目成员模型 (Project Level RBAC)。 用于在更细粒度（项目级）控制用户权限。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `user_id` | UUID | FK | 是 | - | - |
| `gitlab_uid` | Integer | - | 是 | - | - |
| `access_level` | Integer | - | 是 | - | - |
| `role_id` | Integer | FK | 是 | - | - |
| `job_title` | String(100) | - | 是 | - | - |
| `joined_at` | DateTime | - | 是 | - | - |
| `expires_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **role**: many-to-one → `Role`
- **project**: many-to-one → `GitLabProject`
- **user**: many-to-one → `User`

---

### GitLabProject (`gitlab_projects`)

**业务描述**: GitLab 项目模型。 存储 GitLab 中项目的元数据，并关联到组织架构。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `name` | String | - | 是 | - | - |
| `path_with_namespace` | String | - | 是 | - | - |
| `description` | String | - | 是 | - | - |
| `department` | String | - | 是 | - | - |
| `group_id` | Integer | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `last_activity_at` | DateTime | - | 是 | - | - |
| `last_synced_at` | DateTime | - | 是 | - | - |
| `sync_status` | String | - | 是 | PENDING | - |
| `raw_data` | JSON | - | 是 | - | - |
| `sync_state` | JSON | - | 是 | {} | - |
| `storage_size` | BigInteger | - | 是 | - | - |
| `star_count` | Integer | - | 是 | - | - |
| `forks_count` | Integer | - | 是 | - | - |
| `open_issues_count` | Integer | - | 是 | - | - |
| `commit_count` | Integer | - | 是 | - | - |
| `tags_count` | Integer | - | 是 | - | - |
| `branches_count` | Integer | - | 是 | - | - |
| `organization_id` | String(100) | FK | 是 | - | - |
| `mdm_project_id` | String(100) | FK | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **group**: many-to-one → `GitLabGroup`
- **organization**: many-to-one → `Organization`
- **mdm_project**: many-to-one → `ProjectMaster`
- **dependency_scans**: one-to-many → `DependencyScan`
- **dependencies**: one-to-many → `Dependency`
- **milestones**: one-to-many → `GitLabMilestone`
- **members**: one-to-many → `GitLabProjectMember`
- **commits**: one-to-many → `GitLabCommit`
- **merge_requests**: one-to-many → `GitLabMergeRequest`
- **issues**: one-to-many → `GitLabIssue`
- **pipelines**: one-to-many → `GitLabPipeline`
- **deployments**: one-to-many → `GitLabDeployment`
- **test_cases**: one-to-many → `GTMTestCase`
- **requirements**: one-to-many → `GTMRequirement`
- **test_execution_records**: one-to-many → `GTMTestExecutionRecord`
- **sonar_projects**: one-to-many → `SonarProject`
- **jira_projects**: one-to-many → `JiraProject`

---

### GitLabRelease (`gitlab_releases`)

**业务描述**: GitLab 发布记录模型。 对应 GitLab 的 Release 对象。一个 Release 基于一个 Tag，可以关联多个 Milestone。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `tag_name` | String(255) | - | 否 | - | - |
| `name` | String(255) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `released_at` | DateTime | - | 是 | - | - |
| `author_id` | UUID | FK | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`
- **milestones**: one-to-many → `GitLabMilestone`

---

### GitLabTag (`gitlab_tags`)

**业务描述**: 标签/版本号模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `name` | String | - | 是 | - | - |
| `message` | String | - | 是 | - | - |
| `commit_sha` | String | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`

---

## 认证与授权域

### UserCredential (`sys_user_credentials`)

**业务描述**: 用户凭证表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `user_id` | UUID | FK, UNIQUE | 是 | - | - |
| `password_hash` | String(255) | - | 否 | - | - |
| `last_login_at` | DateTime | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **user**: many-to-one → `User`

---

### UserOAuthToken (`sys_user_oauth_tokens`)

**业务描述**: 用户 OAuth 令牌存储表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `user_id` | String(100) | INDEX | 是 | - | - |
| `provider` | String(50) | INDEX | 是 | - | - |
| `access_token` | String(1024) | - | 否 | - | - |
| `refresh_token` | String(1024) | - | 是 | - | - |
| `token_type` | String(50) | - | 是 | - | - |
| `expires_at` | DateTime | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

## 其他辅助域

### CommitMetrics (`commit_metrics`)

**业务描述**: 单个提交的详细度量数据 (ELOC)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `commit_id` | String(100) | PK | 否 | - | - |
| `project_id` | String(100) | FK | 是 | - | - |
| `author_email` | String(255) | INDEX | 是 | - | - |
| `committed_at` | DateTime | - | 是 | - | - |
| `raw_additions` | Integer | - | 是 | 0 | - |
| `raw_deletions` | Integer | - | 是 | 0 | - |
| `eloc_score` | Numeric | - | 是 | 0.0 | - |
| `impact_score` | Numeric | - | 是 | 0.0 | - |
| `churn_lines` | Integer | - | 是 | 0 | - |
| `comment_lines` | Integer | - | 是 | 0 | - |
| `test_lines` | Integer | - | 是 | 0 | - |
| `file_count` | Integer | - | 是 | 0 | - |
| `is_merge` | Boolean | - | 是 | False | - |
| `is_legacy_refactor` | Boolean | - | 是 | False | - |
| `refactor_ratio` | Numeric | - | 是 | 0.0 | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### DailyDevStats (`daily_dev_stats`)

**业务描述**: 开发人员行为的每日快照。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `user_id` | UUID | FK, INDEX | 是 | - | - |
| `date` | DATE | INDEX | 是 | - | - |
| `first_commit_time` | DateTime | - | 是 | - | - |
| `last_commit_time` | DateTime | - | 是 | - | - |
| `commit_count` | Integer | - | 是 | 0 | - |
| `total_impact` | Numeric | - | 是 | 0.0 | - |
| `total_churn` | Integer | - | 是 | 0 | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### Dependency (`dependencies`)

**业务描述**: 项目依赖清单表 (dependencies)。 存储扫描发现的每一个具体的三方类库及其安全和合规状态。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `scan_id` | Integer | FK | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `package_name` | String(500) | - | 否 | - | - |
| `package_version` | String(100) | - | 是 | - | - |
| `package_manager` | String(50) | - | 是 | - | - |
| `dependency_type` | String(20) | - | 是 | direct | - |
| `license_name` | String(200) | - | 是 | - | - |
| `license_spdx_id` | String(100) | - | 是 | - | - |
| `license_url` | Text | - | 是 | - | - |
| `license_risk_level` | String(20) | - | 是 | - | - |
| `has_vulnerabilities` | Boolean | - | 是 | False | - |
| `highest_cvss_score` | Numeric | - | 是 | - | - |
| `critical_cve_count` | Integer | - | 是 | 0 | - |
| `high_cve_count` | Integer | - | 是 | 0 | - |
| `medium_cve_count` | Integer | - | 是 | 0 | - |
| `low_cve_count` | Integer | - | 是 | 0 | - |
| `file_path` | Text | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `homepage_url` | Text | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **scan**: many-to-one → `DependencyScan`
- **project**: many-to-one → `GitLabProject`
- **cves**: one-to-many → `DependencyCVE`

---

### DependencyCVE (`dependency_cves`)

**业务描述**: CVE 漏洞详情表 (dependency_cves)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `dependency_id` | Integer | FK | 否 | - | - |
| `cve_id` | String(50) | - | 否 | - | - |
| `cvss_score` | Numeric | - | 是 | - | - |
| `cvss_vector` | String(200) | - | 是 | - | - |
| `severity` | String(20) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `published_date` | DateTime | - | 是 | - | - |
| `last_modified_date` | DateTime | - | 是 | - | - |
| `fixed_version` | String(100) | - | 是 | - | - |
| `remediation` | Text | - | 是 | - | - |
| `references` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **dependency**: many-to-one → `Dependency`

---

### DependencyScan (`dependency_scans`)

**业务描述**: 依赖扫描记录表 (dependency_scans)。 存储 OWASP Dependency-Check 等工具生成的扫描任务概览。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `scan_date` | DateTime | - | 否 | - | - |
| `scanner_name` | String(50) | - | 否 | OWASP Dependency-Check | - |
| `scanner_version` | String(20) | - | 是 | - | - |
| `total_dependencies` | Integer | - | 是 | 0 | - |
| `vulnerable_dependencies` | Integer | - | 是 | 0 | - |
| `high_risk_licenses` | Integer | - | 是 | 0 | - |
| `scan_status` | String(20) | - | 是 | completed | - |
| `report_path` | Text | - | 是 | - | - |
| `raw_json` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `GitLabProject`
- **dependencies**: one-to-many → `Dependency`

---

### PerformanceRecord (`fct_performance_records`)

**业务描述**: 效能/性能表现评估记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |

---

### UserActivityProfile (`fct_user_activity_profiles`)

**业务描述**: 用户活跃度画像快照表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | BigInteger | PK | 否 | - | - |

---

### JiraBoard (`jira_boards`)

**业务描述**: Jira 看板模型 (jira_boards)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `name` | String(255) | - | 是 | - | - |
| `type` | String(50) | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `JiraProject`
- **sprints**: one-to-many → `JiraSprint`

---

### JiraIssue (`jira_issues`)

**业务描述**: Jira Issue (问题/任务) 详情模型 (jira_issues)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `key` | String(50) | UNIQUE | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `sprint_id` | Integer | FK | 是 | - | - |
| `summary` | String(500) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `status` | String(50) | - | 是 | - | - |
| `priority` | String(50) | - | 是 | - | - |
| `issue_type` | String(50) | - | 是 | - | - |
| `assignee_name` | String(255) | - | 是 | - | - |
| `reporter_name` | String(255) | - | 是 | - | - |
| `creator_name` | String(255) | - | 是 | - | - |
| `assignee_user_id` | UUID | FK | 是 | - | - |
| `reporter_user_id` | UUID | FK | 是 | - | - |
| `creator_user_id` | UUID | FK | 是 | - | - |
| `user_id` | UUID | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `resolved_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `first_commit_sha` | String(100) | - | 是 | - | - |
| `first_fix_date` | DateTime | - | 是 | - | - |
| `reopening_count` | Integer | - | 是 | 0 | - |
| `time_to_first_response` | BigInteger | - | 是 | - | - |
| `original_estimate` | BigInteger | - | 是 | - | - |
| `time_spent` | BigInteger | - | 是 | - | - |
| `remaining_estimate` | BigInteger | - | 是 | - | - |
| `labels` | JSON | - | 是 | - | - |
| `fix_versions` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `JiraProject`
- **history**: one-to-many → `JiraIssueHistory`
- **sprint**: many-to-one → `JiraSprint`

---

### JiraProject (`jira_projects`)

**业务描述**: Jira 项目模型 (jira_projects)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `key` | String(50) | UNIQUE | 否 | - | - |
| `name` | String(255) | - | 否 | - | - |
| `description` | Text | - | 是 | - | - |
| `lead_name` | String(255) | - | 是 | - | - |
| `gitlab_project_id` | Integer | FK | 是 | - | - |
| `last_synced_at` | DateTime | - | 是 | - | - |
| `sync_status` | String(20) | - | 是 | PENDING | - |
| `created_at` | DateTime | - | 是 | <function JiraProject.<lambda> at 0x00000235C02CE840> | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **gitlab_project**: many-to-one → `GitLabProject`
- **boards**: one-to-many → `JiraBoard`
- **issues**: one-to-many → `JiraIssue`

---

### JiraSprint (`jira_sprints`)

**业务描述**: Jira Sprint (迭代) 模型 (jira_sprints)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `board_id` | Integer | FK | 否 | - | - |
| `name` | String(255) | - | 是 | - | - |
| `state` | String(20) | - | 是 | - | - |
| `start_date` | DateTime | - | 是 | - | - |
| `end_date` | DateTime | - | 是 | - | - |
| `complete_date` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **board**: many-to-one → `JiraBoard`
- **issues**: one-to-many → `JiraIssue`

---

### LicenseRiskRule (`license_risk_rules`)

**业务描述**: 许可证风险规则配置表 (license_risk_rules)。 用于定义不同开源许可证的合规性风险评级。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `license_name` | String(200) | UNIQUE | 否 | - | - |
| `license_spdx_id` | String(100) | - | 是 | - | - |
| `risk_level` | String(20) | - | 否 | - | - |
| `is_copyleft` | Boolean | - | 是 | False | - |
| `commercial_use_allowed` | Boolean | - | 是 | True | - |
| `modification_allowed` | Boolean | - | 是 | True | - |
| `distribution_allowed` | Boolean | - | 是 | True | - |
| `patent_grant` | Boolean | - | 是 | False | - |
| `description` | Text | - | 是 | - | - |
| `policy_notes` | Text | - | 是 | - | - |
| `is_active` | Boolean | - | 是 | True | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### Permission (`rbac_permissions`)

**业务描述**: 原子权限定义表 (rbac_permissions)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `code` | String(100) | PK | 否 | - | - |
| `category` | String(50) | - | 是 | - | - |
| `description` | String(255) | - | 是 | - | - |

#### 关系映射

- **roles**: one-to-many → `Role`

---

### Role (`rbac_roles`)

**业务描述**: 系统角色参考表 (rbac_roles)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `code` | String(50) | UNIQUE | 否 | - | - |
| `name` | String(100) | UNIQUE | 否 | - | - |
| `description` | String(255) | - | 是 | - | - |

#### 关系映射

- **permissions**: one-to-many → `Permission`
- **users**: one-to-many → `User`

---

### SonarIssue (`sonar_issues`)

**业务描述**: SonarQube 问题详情模型 (sonar_issues)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `issue_key` | String(50) | UNIQUE | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `type` | String(20) | - | 是 | - | - |
| `severity` | String(20) | - | 是 | - | - |
| `status` | String(20) | - | 是 | - | - |
| `resolution` | String(20) | - | 是 | - | - |
| `rule` | String(200) | - | 是 | - | - |
| `message` | Text | - | 是 | - | - |
| `component` | String(500) | - | 是 | - | - |
| `line` | Integer | - | 是 | - | - |
| `effort` | String(20) | - | 是 | - | - |
| `debt` | String(20) | - | 是 | - | - |
| `creation_date` | DateTime | - | 是 | - | - |
| `update_date` | DateTime | - | 是 | - | - |
| `close_date` | DateTime | - | 是 | - | - |
| `assignee` | String(100) | - | 是 | - | - |
| `author` | String(100) | - | 是 | - | - |
| `assignee_user_id` | UUID | FK | 是 | - | - |
| `author_user_id` | UUID | FK | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `SonarProject`

---

### SonarMeasure (`sonar_measures`)

**业务描述**: SonarQube 指标快照模型 (sonar_measures)。 每次代码分析后记录一条快照，用于追踪质量趋势。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 否 | - | - |
| `analysis_date` | DateTime | - | 否 | - | - |
| `files` | Integer | - | 是 | - | - |
| `lines` | Integer | - | 是 | - | - |
| `ncloc` | Integer | - | 是 | - | - |
| `classes` | Integer | - | 是 | - | - |
| `functions` | Integer | - | 是 | - | - |
| `statements` | Integer | - | 是 | - | - |
| `coverage` | Numeric | - | 是 | - | - |
| `bugs` | Integer | - | 是 | - | - |
| `bugs_blocker` | Integer | - | 是 | 0 | - |
| `bugs_critical` | Integer | - | 是 | 0 | - |
| `bugs_major` | Integer | - | 是 | 0 | - |
| `bugs_minor` | Integer | - | 是 | 0 | - |
| `bugs_info` | Integer | - | 是 | 0 | - |
| `vulnerabilities` | Integer | - | 是 | - | - |
| `vulnerabilities_blocker` | Integer | - | 是 | 0 | - |
| `vulnerabilities_critical` | Integer | - | 是 | 0 | - |
| `vulnerabilities_major` | Integer | - | 是 | 0 | - |
| `vulnerabilities_minor` | Integer | - | 是 | 0 | - |
| `vulnerabilities_info` | Integer | - | 是 | 0 | - |
| `security_hotspots` | Integer | - | 是 | - | - |
| `security_hotspots_high` | Integer | - | 是 | 0 | - |
| `security_hotspots_medium` | Integer | - | 是 | 0 | - |
| `security_hotspots_low` | Integer | - | 是 | 0 | - |
| `code_smells` | Integer | - | 是 | - | - |
| `comment_lines_density` | Numeric | - | 是 | - | - |
| `duplicated_lines_density` | Numeric | - | 是 | - | - |
| `sqale_index` | Integer | - | 是 | - | - |
| `sqale_debt_ratio` | Numeric | - | 是 | - | - |
| `complexity` | Integer | - | 是 | - | - |
| `cognitive_complexity` | Integer | - | 是 | - | - |
| `reliability_rating` | String(1) | - | 是 | - | - |
| `security_rating` | String(1) | - | 是 | - | - |
| `sqale_rating` | String(1) | - | 是 | - | - |
| `quality_gate_status` | String(10) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function SonarMeasure.<lambda> at 0x00000235C029CEA0> | - |

#### 关系映射

- **project**: many-to-one → `SonarProject`

---

### SonarProject (`sonar_projects`)

**业务描述**: SonarQube 项目模型 (sonar_projects)。 存储 SonarQube 项目信息，支持与 GitLab 项目关联。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `key` | String(500) | UNIQUE | 否 | - | - |
| `name` | String(255) | - | 是 | - | - |
| `qualifier` | String(10) | - | 是 | - | - |
| `gitlab_project_id` | Integer | FK | 是 | - | - |
| `last_analysis_date` | DateTime | - | 是 | - | - |
| `last_synced_at` | DateTime | - | 是 | - | - |
| `sync_status` | String(20) | - | 是 | PENDING | - |
| `created_at` | DateTime | - | 是 | <function SonarProject.<lambda> at 0x00000235C027B2E0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **gitlab_project**: many-to-one → `GitLabProject`
- **measures**: one-to-many → `SonarMeasure`
- **issues**: one-to-many → `SonarIssue`
- **latest_measure**: many-to-one → `SonarMeasure`

---

### RawDataStaging (`stg_raw_data`)

**业务描述**: 原始数据暂存表 (Staging 层)，用于存放未经处理的 API Payload。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `source` | String(50) | - | 是 | - | - |
| `entity_type` | String(50) | - | 是 | - | - |
| `external_id` | String(100) | - | 是 | - | - |
| `payload` | JSON | - | 是 | - | - |
| `schema_version` | String(20) | - | 是 | - | - |
| `collected_at` | DateTime | - | 是 | - | - |

---

### RolePermission (`sys_role_permissions`)

**业务描述**: 角色与权限映射表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `role_id` | Integer | PK, FK | 否 | - | - |
| `permission_code` | String(100) | PK, FK | 否 | - | - |

---

### SyncLog (`sys_sync_logs`)

**业务描述**: 插件数据同步日志记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | String(100) | INDEX | 是 | - | - |
| `status` | String(50) | - | 是 | - | - |
| `message` | Text | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### TeamMember (`sys_team_members`)

**业务描述**: 团队成员关联表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `team_id` | Integer | FK | 否 | - | - |
| `user_id` | UUID | FK | 否 | - | - |
| `role_code` | String(50) | - | 是 | MEMBER | - |
| `allocation_ratio` | Numeric | - | 是 | 1.0 | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **team**: many-to-one → `Team`
- **user**: many-to-one → `User`

---

### Team (`sys_teams`)

**业务描述**: 虚拟业务团队/项目组表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `name` | String(100) | - | 否 | - | - |
| `team_code` | String(50) | UNIQUE, INDEX | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `parent_id` | Integer | FK | 是 | - | - |
| `org_id` | String(100) | FK | 是 | - | - |
| `leader_id` | UUID | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x00000235BE8320C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **parent**: many-to-one → `Team`
- **leader**: many-to-one → `User`
- **members**: one-to-many → `TeamMember`
- **children**: one-to-many → `Team`

---

### UserRole (`sys_user_roles`)

**业务描述**: 用户与角色映射表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `user_id` | UUID | PK, FK | 否 | - | - |
| `role_id` | Integer | PK, FK | 否 | - | - |

---


## 变更日志

### v2.1 (2025-01-16)
- 基于最新 SQLAlchemy 模型自动生成
- 移除所有表情符号以符合规范
- 新增企业级分域架构组织
- 完善字段约束和关系映射说明

---

**维护说明**: 本文档由 `scripts/generate_data_dictionary.py` 自动生成，请勿手动编辑！如需更新，请修改模型定义并重新运行生成脚本。

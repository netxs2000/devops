# 📊 DevOps 效能平台 - 数据字典 (Data Dictionary)

> **生成时间**: 2026-01-06 16:00:00  
> **版本**: v4.0 (Refactored)  
> **状态**: ✅ 有效 (Active)

---

## 📖 文档说明

本数据字典基于系统最新的 SQLAlchemy ORM 模型自动生成，确保与实际数据库结构的一致性。

### 文档结构

- **表名**: 数据库表的物理名称
- **模型类**: 对应的 Python ORM 模型类名
- **业务描述**: 从模型 Docstring 提取的业务用途说明
- **字段定义**: 包含字段名、类型、约束、可空性、默认值和业务说明
- **关系映射**: 表间的 ORM 关系（一对多、多对一等）

---

## 📋 数据表清单

本系统共包含 **65 个基础表** 以及 **15 个高级智能分析模型**，分为以下几个业务域：

### 🏢 核心主数据域 (Core Master Data)

- `mdm_calendar` - Calendar
- mdm_identities - User
- mdm_identity_mappings - IdentityMapping
- mdm_location - Location
- mdm_organizations - Organization
- products - Product
- services - Service

### 🧪 测试管理域 (Test Management)

- `gtm_requirements` - GTMRequirement
- `gtm_test_case_issue_links` - GTMTestCaseIssueLink
- `gtm_test_cases` - GTMTestCase
- `gtm_test_execution_records` - GTMTestExecutionRecord
- `test_execution_summaries` - TestExecutionSummary

### 🦊 GitLab 集成域 (GitLab Integration)

- `gitlab_dependencies` - GitLabDependency
- `gitlab_group_members` - GitLabGroupMember
- `gitlab_groups` - GitLabGroup
- `gitlab_issue_events` - GitLabIssueEvent
- `gitlab_package_files` - GitLabPackageFile
- `gitlab_packages` - GitLabPackage
- `gitlab_project_members` - ProjectMember
- `gitlab_wiki_logs` - GitLabWikiLog
- `sync_logs` - SyncLog

### 📈 分析与洞察域 (Analytics & Insights)

- `okr_key_results` - OKRKeyResult
- `okr_objectives` - OKRObjective

### 🗂️ 其他辅助域 (Other Supporting Tables)

- `branches` - Branch
- `commit_file_stats` - CommitFileStats
- `commits` - Commit
- `dependencies` - Dependency
- `dependency_cves` - DependencyCVE
- `dependency_scans` - DependencyScan
- `deployments` - Deployment
- `incidents` - Incident
- `issues` - Issue
- `jenkins_builds` - JenkinsBuild
- `jenkins_jobs` - JenkinsJob
- `jfrog_artifacts` - JFrogArtifact
- `jfrog_dependencies` - JFrogDependency
- `jfrog_scans` - JFrogScan
- `jfrog_vulnerability_details` - JFrogVulnerabilityDetail
- `jira_boards` - JiraBoard
- `jira_issue_histories` - JiraIssueHistory
- `jira_issues` - JiraIssue
- `jira_projects` - JiraProject
- `jira_sprints` - JiraSprint
- `license_risk_rules` - LicenseRiskRule
- `merge_requests` - MergeRequest
- `milestones` - Milestone
- `nexus_assets` - NexusAsset
- `nexus_components` - NexusComponent
- `notes` - Note
- `performance_records` - PerformanceRecord
- `pipelines` - Pipeline
- `projects` - Project
- `raw_data_staging` - RawDataStaging
- `resource_costs` - ResourceCost
- `service_project_mappings` - ServiceProjectMapping
- `slos` - SLO
- `sonar_issues` - SonarIssue
- `sonar_measures` - SonarMeasure
- `sonar_projects` - SonarProject
- `tags` - Tag
- `traceability_links` - TraceabilityLink
- `user_activity_profiles` - UserActivityProfile
- `zentao_executions` - ZenTaoExecution
- `zentao_issues` - ZenTaoIssue
- `zentao_products` - ZenTaoProduct

### 🧠 高级智能分析域 (Advanced Intelligence Models - dbt)

- `int_unified_activities` - 统一活动流引擎
- `int_entity_alignment` - 模糊实体对齐与链接
- `fct_developer_activity_profile` - 开发者 DNA 画像
- `fct_capitalization_audit` - 研发投入资本化审计
- `fct_delivery_costs` - 交付成本与 FinOps 桥接指标
- `fct_metrics_audit_guard` - 指标一致性哨兵
- `fct_shadow_it_discovery` - 影子系统发现 (Shadow IT)
- `fct_dora_metrics` - DORA 核心度量
- `fct_project_delivery_health` - 项目交付健康度 360
- `fct_compliance_audit` - 合规与内控审计
- `fct_architectural_brittleness` - 架构脆性指数 (ABI)
- `fct_talent_radar` - 人才雷达识别
- `int_unified_work_items` - 统一扁平化工作项引擎

---

## 📦 核心主数据域

### Calendar (`mdm_calendar`)

**业务描述**: 万年历主数据 (mdm_calendar)。 提供日期维度的全量属性，支持跨地域法定节假日、工作日判定，是 DORA 流动效能、人力成本核算及研发 ROI 计算的时间基准。

#### 字段定义 - Calendar

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `date_id` | Integer | PK | 否 | - | 日期主键 (YYYYMMDD) |
| `full_date` | Date | - | 否 | - | 完整日期 |
| `year` | Integer | - | 否 | - | 年份 |
| `month` | Integer | - | 否 | - | 月份 (1-12) |
| `day` | Integer | - | 否 | - | 日 (1-31) |
| `quarter` | Integer | - | 否 | - | 季度 (1-4) |
| `week_of_year` | Integer | - | 否 | - | 一年中的第几周 |
| `day_of_week` | Integer | - | 否 | - | 星期几 (0-6, 0=Sunday) |
| `is_workday` | Boolean | - | 否 | True | 是否为工作日 (考虑调休) |
| `is_holiday` | Boolean | - | 否 | False | 是否为法定节假日 |
| `holiday_name` | String(100) | - | 是 | - | 节假日名称 (如：春节) |
| `region` | String(20) | - | 否 | CN | 区域 (默认 CN) |
| `fiscal_year` | Integer | - | 是 | - | 财年 |
| `created_at` | DateTime | - | 是 | now() | 创建时间 |

---

### User (`mdm_identities`)

**业务描述**: 人员主数据 (mdm_identities)。 全局唯一标识，集团级唯一身份 ID (OneID)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 否 | - | - |
| `global_user_id` | UUID | - | 否 | - | - |
| `employee_id` | String(50) | - | 是 | - | - |
| `full_name` | String(200) | - | 否 | - | - |
| `primary_email` | String(200) | - | 是 | - | - |
| `identity_map` | JSONB | - | 是 | - | - |
| `match_confidence` | Numeric | - | 是 | - | - |
| `is_survivor` | Boolean | - | 是 | True | - |
| `is_active` | Boolean | - | 是 | True | - |
| `sync_version` | BigInteger | - | 否 | 1 | - |
| `is_deleted` | Boolean | - | 否 | False | - |
| `effective_from` | DateTime | - | 否 | 系统默认 | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | - | 否 | True | - |
| `created_at` | DateTime | - | 是 | 系统默认 | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `source_system` | String(50) | - | 是 | - | - |
| `department_id` | String(100) | FK | 是 | - | - |
| `location_id` | String(6) | FK | 是 | - | - |

#### 关系映射

- **department**: many-to-one → `Organization`
- **location**: many-to-one → `Location`
- **managed_organizations**: one-to-many → `Organization`
- **roles**: one-to-many → `Role`
- **identities**: one-to-many → `IdentityMapping`
- **activity_profiles**: one-to-many → `UserActivityProfile`
- **okr_objectives**: one-to-many → `OKRObjective`
- **test_cases**: one-to-many → `GTMTestCase`
- **requirements**: one-to-many → `GTMRequirement`
- **managed_products_as_pm**: one-to-many → `Product`
- **managed_products_as_dm**: one-to-many → `Product`
- **managed_products_as_tm**: one-to-many → `Product`
- **managed_products_as_rm**: one-to-many → `Product`
- **project_memberships**: one-to-many → `ProjectMember`
- **credential**: many-to-one → `UserCredential`

---

### IdentityMapping (`mdm_identity_mappings`)

**业务描述**: 身份映射关系表 (mdm_identity_mappings)。 存储 OneID 到各子系统的具体账号 ID。

#### 字段定义 - IdentityMapping

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 否 | - | - |
| `global_user_id` | UUID | FK | 是 | - | - |
| `source_system` | String(50) | - | 否 | - | - |
| `external_user_id` | String(100) | - | 否 | - | - |
| `external_username` | String(100) | - | 是 | - | - |
| `external_email` | String(200) | - | 是 | - | - |
| `mapping_type` | String(20) | - | 是 | automatic | - |
| `last_seen_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **user**: many-to-one → `User`

---

### Location (`mdm_location`)

**业务描述**: 地理位置主数据 (mdm_location)。 为支持省、市、区县三级层级结构，采用统一地址代码表结构（适配 GB/T 2260 国标）。

#### 字段定义 - Location

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `location_id` | String(6) | PK | 否 | - | - |
| `location_name` | String(50) | - | 否 | - | - |
| `location_type` | String(20) | - | 否 | - | - |
| `parent_id` | String(6) | FK | 是 | - | - |
| `short_name` | String(20) | - | 否 | - | - |
| `region` | String(10) | - | 否 | - | - |
| `is_active` | Boolean | - | 是 | True | - |
| `manager_user_id` | UUID | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function Location.<lambda> at 0x0000022FBD1CA400> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射 - Location

- **children**: one-to-many → `Location`
- **manager**: many-to-one → `User`
- **parent**: many-to-one → `Location`

---

### Organization (`mdm_organizations`)

**业务描述**: 组织架构主数据 (mdm_organizations)。 建立全集团的汇报线与成本中心映射，支持指标按部门层级汇总。

#### 字段定义 - Organization

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 否 | - | - |
| `org_id` | String(100) | - | 否 | - | - |
| `org_name` | String(200) | - | 否 | - | - |
| `parent_org_id` | String(100) | FK | 是 | - | - |
| `org_level` | Integer | - | 是 | - | - |
| `manager_user_id` | UUID | FK | 是 | - | - |
| `cost_center` | String(100) | - | 是 | - | - |
| `sync_version` | BigInteger | - | 否 | 1 | - |
| `is_deleted` | Boolean | - | 否 | False | - |
| `effective_from` | DateTime | - | 否 | <function Organization.<lambda> at 0x0000022FBD1C94E0> | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | - | 否 | True | - |
| `created_at` | DateTime | - | 是 | <function Organization.<lambda> at 0x0000022FBD1C9900> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射 - Organization

- **children**: one-to-many → `Organization`
- **services**: one-to-many → `Service`
- **manager**: many-to-one → `User`
- **users**: one-to-many → `User`
- **products**: one-to-many → `Product`
- **okr_objectives**: one-to-many → `OKRObjective`
- **revenue_contracts**: one-to-many → `RevenueContract`
- **projects**: one-to-many → `Project`
- **parent**: many-to-one → `Organization`

---

### Product (`products`)

**业务描述**: 全局产品模型，支持“产品线 -> 产品”的层级结构。 用于在业务层面聚合技术项目和负责人，是多项目协作和成本分析的基础。

#### 字段定义 - Product

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | Integer | PK | 否 | - | - |
| `name` | String(200) | - | 否 | - | - |
| `description` | Text | - | 是 | - | - |
| `level` | String(20) | - | 是 | - | - |
| `parent_id` | Integer | FK | 是 | - | - |
| `product_line_name` | String(200) | - | 是 | - | - |
| `organization_id` | String(100) | FK | 是 | - | - |
| `finance_code` | String(100) | - | 是 | - | - |
| `project_id` | Integer | - | 是 | - | - |
| `external_epic_id` | String(100) | - | 是 | - | - |
| `external_goal_id` | String(100) | - | 是 | - | - |
| `source_system` | String(50) | - | 是 | - | - |
| `product_manager_id` | UUID | FK | 是 | - | - |
| `dev_manager_id` | UUID | FK | 是 | - | - |
| `test_manager_id` | UUID | FK | 是 | - | - |
| `release_manager_id` | UUID | FK | 是 | - | - |
| `budget_amount` | Numeric | - | 是 | - | - |
| `business_value_score` | Integer | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function Product.<lambda> at 0x0000022FBD22B950> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射 - Product

- **children**: one-to-many → `Product`
- **organization**: many-to-one → `Organization`
- **product_manager**: many-to-one → `User`
- **dev_manager**: many-to-one → `User`
- **test_manager**: many-to-one → `User`
- **release_manager**: many-to-one → `User`
- **revenue_contracts**: one-to-many → `RevenueContract`
- **objectives**: one-to-many → `OKRObjective`
- **parent**: many-to-one → `Product`

---

### Service (`services`)

**业务描述**: 服务目录模型 (Service Catalog)。 用于在逻辑层面定义业务服务，一个服务可能对应多个技术项目(Repositories)。 跨越 DevOps L4 的核心元数据。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `name` | String(200) | UNIQUE | 否 | - | - |
| `tier` | String(20) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `organization_id` | String(100) | FK | 是 | - | - |
| `product_id` | Integer | FK | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x0000022FBD1C8EB0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **organization**: many-to-one → `Organization`
- **product**: many-to-one → `Product`
- **slos**: one-to-many → `SLO`
- **projects**: one-to-many → `ServiceProjectMapping`
- **resource_costs**: one-to-many → `ResourceCost`

---

## 📦 测试管理域

### GTMRequirement (`gtm_requirements`)

**业务描述**: GTM 需求模型 (GitLab Test Management Requirement)。 代表业务层面的功能需求，用于实现从需求到测试用例的端到端追溯。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `project_id` | Integer | FK | 否 | - | 关联项目 ID |
| `author_id` | UUID | FK | 否 | - | 创建者 (User.global_user_id) |
| `iid` | Integer | - | 否 | - | 内部 ID (Internal ID) |
| `title` | String(255) | - | 否 | - | 需求标题 |
| `description` | Text | - | 是 | - | 需求详述 |
| `state` | String(20) | - | 是 | opened | 状态 (opened/closed) |
| `created_at` | DateTime | - | 是 | now() | 创建时间 |
| `updated_at` | DateTime | - | 是 | - | 更新时间 |

#### 关系映射

- **author**: many-to-one → `User`
- **project**: many-to-one → `Project`
- **test_cases**: one-to-many → `GTMTestCase`

---

### GTMTestCaseIssueLink (`gtm_test_case_issue_links`)

**业务描述**: GTM 测试用例与 Issue 的多对多关联表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 主键 |
| `test_case_id` | Integer | FK | 否 | - | 关联测试用例 ID |
| `issue_id` | Integer | FK | 否 | - | 关联 Issue ID |
| `created_at` | DateTime | - | 是 | now() | 创建时间 |
| `updated_at` | DateTime | - | 是 | - | 更新时间 |

---

### GTMTestCase (`gtm_test_cases`)

**业务描述**: GTM 测试用例模型 (GitLab Test Management TestCase)。 存储测试用例的结构化信息，包括标题、描述（预置条件）和详细的执行步骤。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `project_id` | Integer | FK | 否 | - | 关联项目 ID |
| `author_id` | UUID | FK | 否 | - | 创建者 ID |
| `iid` | Integer | - | 否 | - | 内部 ID |
| `title` | String(255) | - | 否 | - | 用例标题 |
| `priority` | String(20) | - | 是 | - | 优先级 |
| `test_type` | String(50) | - | 是 | - | 测试类型 |
| `pre_conditions` | Text | - | 是 | - | 前置条件 |
| `description` | Text | - | 是 | - | 用例详述 |
| `test_steps` | JSON | - | 是 | [] | 测试步骤 |
| `created_at` | DateTime | - | 是 | now() | 创建时间 |
| `updated_at` | DateTime | - | 是 | - | 更新时间 |

#### 关系映射

- **author**: many-to-one → `User`
- **project**: many-to-one → `Project`
- **linked_issues**: one-to-many → `Issue` (via `gtm_test_case_issue_links`)
- **associated_requirements**: one-to-many → `GTMRequirement`
- **execution_records**: one-to-many → `GTMTestExecutionRecord`

---

### GTMTestExecutionRecord (`gtm_test_execution_records`)

**业务描述**: GTM 测试执行审计记录模型。 记录单次测试用例的执行结果。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 主键 |
| `project_id` | Integer | FK | 否 | - | 关联项目 ID |
| `test_case_iid` | Integer | INDEX | 否 | - | 关联用例的 IID |
| `result` | String(20) | - | 否 | - | 执行结果 (passed/failed/etc.) |
| `executed_at` | DateTime | - | 是 | now() | 执行时间 |
| `executor_name` | String(100) | - | 是 | - | 执行人姓名 |
| `executor_uid` | UUID | - | 是 | - | 执行人 OneID |
| `comment` | Text | - | 是 | - | 备注/评论 |
| `pipeline_id` | Integer | - | 是 | - | 关联流水线 ID |
| `environment` | String(50) | - | 是 | Default | 测试环境 |
| `title` | String(255) | - | 是 | - | 运行标题 |
| `created_at` | DateTime | - | 是 | now() | 创建时间 |
| `updated_at` | DateTime | - | 是 | - | 更新时间 |

#### 关系映射

- **project**: many-to-one → `Project`

---

### TestExecutionSummary (`test_execution_summaries`)

**业务描述**: 测试执行汇总记录模型。 聚合单次构建或测试任务的全量结果。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 主键 |
| `project_id` | Integer | - | 是 | - | 项目 ID |
| `build_id` | String(100) | - | 是 | - | 构建 ID |
| `test_level` | String(50) | - | 否 | - | 测试层级 |
| `test_tool` | String(50) | - | 是 | - | 测试工具 |
| `total_cases` | Integer | - | 是 | 0 | 总用例数 |
| `passed_count` | Integer | - | 是 | 0 | 通过数 |
| `failed_count` | Integer | - | 是 | 0 | 失败数 |
| `skipped_count` | Integer | - | 是 | 0 | 跳过数 |
| `pass_rate` | Numeric | - | 是 | - | 通过率 |
| `duration_ms` | BigInteger | - | 是 | - | 耗时 (ms) |
| `raw_data` | JSON | - | 是 | - | 原始数据 |
| `created_at` | DateTime | - | 是 | now() | 创建时间 |
| `updated_at` | DateTime | - | 是 | - | 更新时间 |

---

## 📦 GitLab 集成域

### GitLabDependency (`gitlab_dependencies`)

**业务描述**: GitLab 项目依赖模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `name` | String(255) | - | 否 | - | - |
| `version` | String(100) | - | 是 | - | - |
| `package_manager` | String(50) | - | 是 | - | - |
| `dependency_type` | String(50) | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `Project`

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
- **projects**: one-to-many → `Project`
- **members**: one-to-many → `GitLabGroupMember`
- **parent**: many-to-one → `GitLabGroup`

---

### GitLabIssueEvent (`gitlab_issue_events`)

**业务描述**: GitLab Issue 变更事件流。 CALMS 扫描核心表，用于根据事件流重建 Issue 的状态演进过程（如前置时间计算）。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `issue_id` | Integer | FK | 是 | - | - |
| `user_id` | UUID | FK | 是 | - | - |
| `event_type` | String(50) | - | 是 | - | - |
| `action` | String(50) | - | 是 | - | - |
| `external_event_id` | Integer | - | 是 | - | - |
| `meta_info` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **issue**: many-to-one → `Issue`
- **user**: many-to-one → `User`

---

### GitLabPackageFile (`gitlab_package_files`)

**业务描述**: GitLab 包关联的文件模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `package_id` | Integer | FK | 是 | - | - |
| `file_name` | String(255) | - | 否 | - | - |
| `size` | BigInteger | - | 是 | - | - |
| `file_sha1` | String(40) | - | 是 | - | - |
| `file_sha256` | String(64) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **package**: many-to-one → `GitLabPackage`

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

- **project**: many-to-one → `Project`
- **files**: one-to-many → `GitLabPackageFile`

---

### ProjectMember (`gitlab_project_members`)

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
- **project**: many-to-one → `Project`
- **user**: many-to-one → `User`

---

### GitLabWikiLog (`gitlab_wiki_logs`)

**业务描述**: GitLab Wiki 变更日志模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | FK | 是 | - | - |
| `title` | String(255) | - | 是 | - | - |
| `slug` | String(255) | - | 是 | - | - |
| `format` | String(20) | - | 是 | - | - |
| `action` | String(50) | - | 是 | - | - |
| `user_id` | UUID | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `Project`
- **user**: many-to-one → `User`

---

### SyncLog (`sync_logs`)

**业务描述**: 同步任务执行日志模型。 记录采集器每次同步的执行状态与统计信息。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `source` | String(50) | INDEX | 是 | - | - |
| `entity_type` | String(50) | INDEX | 是 | - | - |
| `status` | String(20) | - | 是 | - | - |
| `started_at` | DateTime | - | 是 | - | - |
| `finished_at` | DateTime | - | 是 | - | - |
| `records_processed` | Integer | - | 是 | 0 | - |
| `records_created` | Integer | - | 是 | 0 | - |
| `records_updated` | Integer | - | 是 | 0 | - |
| `records_failed` | Integer | - | 是 | 0 | - |
| `error_message` | Text | - | 是 | - | - |

---

## 📦 分析与洞察域

### OKRKeyResult (`okr_key_results`)

**业务描述**: OKR 关键结果模型 (Key Result)。 定义衡量目标完成情况的具体量化指标。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `objective_id` | Integer | FK | 否 | - | - |
| `title` | String(500) | - | 否 | - | - |
| `initial_value` | String(100) | - | 是 | - | - |
| `target_value` | String(100) | - | 是 | - | - |
| `current_value` | String(100) | - | 是 | - | - |
| `metric_unit` | String(50) | - | 是 | - | - |
| `linked_metrics_config` | JSON | - | 是 | - | - |
| `progress` | Integer | - | 是 | 0 | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x0000022FBD1C8EB0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **objective**: many-to-one → `OKRObjective`

---

### OKRObjective (`okr_objectives`)

**业务描述**: OKR 目标模型 (Objective)。 代表战略高度的业务目标，支持多级树形结构进行战略分解（公司 > 中心 > 部门）。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `title` | String(500) | - | 否 | - | - |
| `description` | Text | - | 是 | - | - |
| `owner_id` | UUID | FK | 是 | - | - |
| `organization_id` | String(100) | FK | 是 | - | - |
| `period` | String(50) | - | 是 | - | - |
| `status` | String(20) | - | 是 | draft | - |
| `product_id` | Integer | FK | 是 | - | - |
| `parent_id` | Integer | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x0000022FBD1C8EB0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **product**: many-to-one → `Product`
- **owner**: many-to-one → `User`
- **organization**: many-to-one → `Organization`
- **children**: one-to-many → `OKRObjective`
- **key_results**: one-to-many → `OKRKeyResult`
- **parent**: many-to-one → `OKRObjective`

---

## 📦 其他辅助域

### Branch (`branches`)

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

- **project**: many-to-one → `Project`

---

### CommitFileStats (`commit_file_stats`)

**业务描述**: 提交文件级别统计模型。 用于细粒度分析每次提交中不同类型文件的代码量和注释率。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `commit_id` | String | FK | 是 | - | - |
| `file_path` | String | - | 是 | - | - |
| `language` | String | - | 是 | - | - |
| `file_type_category` | String(50) | - | 是 | - | - |
| `code_added` | Integer | - | 是 | 0 | - |
| `code_deleted` | Integer | - | 是 | 0 | - |
| `comment_added` | Integer | - | 是 | 0 | - |
| `comment_deleted` | Integer | - | 是 | 0 | - |
| `blank_added` | Integer | - | 是 | 0 | - |
| `blank_deleted` | Integer | - | 是 | 0 | - |

#### 关系映射

- **commit**: many-to-one → `Commit`

---

### Commit (`commits`)

**业务描述**: 代码提交记录模型。 存储代码库的每一次提交信息，并关联需求和规范检查状态。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | String | PK | 否 | - | - |
| `project_id` | Integer | PK, FK | 否 | - | - |
| `short_id` | String | - | 是 | - | - |
| `title` | String | - | 是 | - | - |
| `author_name` | String | - | 是 | - | - |
| `author_email` | String | - | 是 | - | - |
| `authored_date` | DateTime | - | 是 | - | - |
| `committed_date` | DateTime | - | 是 | - | - |
| `message` | String | - | 是 | - | - |
| `additions` | Integer | - | 是 | - | - |
| `deletions` | Integer | - | 是 | - | - |
| `total` | Integer | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `linked_issue_ids` | JSON | - | 是 | - | - |
| `issue_source` | String(50) | - | 是 | - | - |
| `is_off_hours` | Boolean | - | 是 | False | - |
| `lint_status` | String(20) | - | 是 | - | - |
| `ai_category` | String(50) | - | 是 | - | - |
| `ai_summary` | Text | - | 是 | - | - |
| `ai_confidence` | Numeric | - | 是 | - | - |
| `gitlab_user_id` | UUID | FK | 是 | - | - |

#### 关系映射

- **author_user**: many-to-one → `User`
- **project**: many-to-one → `Project`

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
| `raw_data` | JSONB | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **scan**: many-to-one → `DependencyScan`
- **project**: many-to-one → `Project`
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
| `references` | JSONB | - | 是 | - | - |
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
| `raw_json` | JSONB | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one → `Project`
- **dependencies**: one-to-many → `Dependency`

---

### Deployment (`deployments`)

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

- **project**: many-to-one → `Project`

---

### Incident (`incidents`)

**业务描述**: 运维事故/故障记录模型。 用于计算 MTTR (平均恢复时间) 和变更失败率。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `external_id` | String(100) | UNIQUE | 是 | - | - |
| `source_system` | String(50) | - | 是 | - | - |
| `title` | String(500) | - | 否 | - | - |
| `description` | Text | - | 是 | - | - |
| `severity` | String(20) | - | 是 | - | - |
| `status` | String(20) | - | 是 | - | - |
| `occurred_at` | DateTime | - | 是 | - | - |
| `resolved_at` | DateTime | - | 是 | - | - |
| `mttr_seconds` | Integer | - | 是 | - | - |
| `project_id` | Integer | - | 是 | - | - |
| `related_deployment_id` | Integer | - | 是 | - | - |
| `related_change_sha` | String(100) | - | 是 | - | - |
| `root_cause_type` | String(50) | - | 是 | - | - |
| `impact_scope` | String(200) | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x0000022FBD1C8EB0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### Issue (`issues`)

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
- **project**: many-to-one → `Project`
- **events**: one-to-many → `GitLabIssueEvent`
- **transitions**: one-to-many → `IssueStateTransition`
- **blockages**: one-to-many → `Blockage`
- **milestone**: many-to-one → `Milestone`
- **merge_requests**: one-to-many → `MergeRequest`
- **associated_test_cases**: one-to-many → `GTMTestCase`

---

### JenkinsBuild (`jenkins_builds`)

**业务描述**: Jenkins 构建(Build)详情模型 (jenkins_builds)。 记录每次构建的具体信息。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `job_id` | Integer | FK | 否 | - | - |
| `number` | Integer | - | 否 | - | - |
| `queue_id` | BigInteger | - | 是 | - | - |
| `url` | String(500) | - | 是 | - | - |
| `result` | String(20) | - | 是 | - | - |
| `duration` | BigInteger | - | 是 | - | - |
| `timestamp` | DateTime | - | 是 | - | - |
| `building` | Boolean | - | 是 | False | - |
| `executor` | String(255) | - | 是 | - | - |
| `trigger_type` | String(50) | - | 是 | - | - |
| `trigger_user` | String(100) | - | 是 | - | - |
| `trigger_user_id` | UUID | FK | 是 | - | - |
| `commit_sha` | String(100) | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `gitlab_mr_iid` | Integer | - | 是 | - | - |
| `artifact_id` | String(200) | - | 是 | - | - |
| `artifact_type` | String(50) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function JenkinsBuild.<lambda> at 0x0000022FBDD47270> | - |

#### 关系映射

- **job**: many-to-one → `JenkinsJob`

---

### JenkinsJob (`jenkins_jobs`)

**业务描述**: Jenkins 任务(Job)模型 (jenkins_jobs)。 存储 Jenkins Job 的基本信息。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `name` | String(255) | - | 否 | - | - |
| `full_name` | String(500) | UNIQUE | 否 | - | - |
| `url` | String(500) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `color` | String(50) | - | 是 | - | - |
| `gitlab_project_id` | Integer | FK | 是 | - | - |
| `last_synced_at` | DateTime | - | 是 | - | - |
| `sync_status` | String(20) | - | 是 | PENDING | - |
| `created_at` | DateTime | - | 是 | <function JenkinsJob.<lambda> at 0x0000022FBDD46980> | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **builds**: one-to-many → `JenkinsBuild`

---

### JFrogArtifact (`jfrog_artifacts`)

**业务描述**: JFrog 制品模型 (jfrog_artifacts)。 存储从 Artifactory 采集的制品元数据，支持 SLSA 溯源。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `repo` | String(100) | - | 否 | - | - |
| `path` | String(500) | - | 否 | - | - |
| `name` | String(200) | - | 否 | - | - |
| `version` | String(100) | - | 是 | - | - |
| `package_type` | String(50) | - | 是 | - | - |
| `size_bytes` | BigInteger | - | 是 | - | - |
| `sha256` | String(64) | - | 是 | - | - |
| `download_count` | Integer | - | 是 | 0 | - |
| `last_downloaded_at` | DateTime | - | 是 | - | - |
| `build_name` | String(200) | - | 是 | - | - |
| `build_number` | String(50) | - | 是 | - | - |
| `build_url` | String(500) | - | 是 | - | - |
| `vcs_url` | String(500) | - | 是 | - | - |
| `vcs_revision` | String(100) | - | 是 | - | - |
| `builder_id` | String(200) | - | 是 | - | - |
| `build_type` | String(100) | - | 是 | - | - |
| `is_signed` | Integer | - | 是 | 0 | - |
| `external_parameters` | JSON | - | 是 | - | - |
| `build_started_at` | DateTime | - | 是 | - | - |
| `build_ended_at` | DateTime | - | 是 | - | - |
| `promotion_status` | String(50) | - | 是 | - | - |
| `properties` | JSON | - | 是 | - | - |
| `created_by_id` | UUID | FK | 是 | - | - |
| `created_by_name` | String(100) | - | 是 | - | - |
| `product_id` | Integer | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **created_by**: many-to-one → `User`
- **product**: many-to-one → `Product`

---

### JFrogDependency (`jfrog_dependencies`)

**业务描述**: 制品依赖树模型 (SBoM)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `artifact_id` | Integer | FK | 是 | - | - |
| `name` | String(200) | - | 否 | - | - |
| `version` | String(100) | - | 是 | - | - |
| `package_type` | String(50) | - | 是 | - | - |
| `scope` | String(50) | - | 是 | - | - |

#### 关系映射

- **artifact**: many-to-one → `JFrogArtifact`

---

### JFrogScan (`jfrog_scans`)

**业务描述**: JFrog Xray 扫描结果模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `artifact_id` | Integer | FK | 是 | - | - |
| `critical_count` | Integer | - | 是 | 0 | - |
| `high_count` | Integer | - | 是 | 0 | - |
| `medium_count` | Integer | - | 是 | 0 | - |
| `low_count` | Integer | - | 是 | 0 | - |
| `violation_count` | Integer | - | 是 | 0 | - |
| `is_compliant` | Integer | - | 是 | - | - |
| `scan_time` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **artifact**: many-to-one → `JFrogArtifact`

---

### JFrogVulnerabilityDetail (`jfrog_vulnerability_details`)

**业务描述**: 漏洞详情明细表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `artifact_id` | Integer | FK | 是 | - | - |
| `cve_id` | String(50) | INDEX | 是 | - | - |
| `severity` | String(20) | - | 是 | - | - |
| `cvss_score` | Numeric | - | 是 | - | - |
| `component` | String(200) | - | 是 | - | - |
| `fixed_version` | String(100) | - | 是 | - | - |
| `description` | String | - | 是 | - | - |

#### 关系映射

- **artifact**: many-to-one → `JFrogArtifact`

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

### JiraIssueHistory (`jira_issue_histories`)

**业务描述**: Jira 问题变更历史表 (jira_issue_histories)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | String(50) | PK | 否 | - | - |
| `issue_id` | Integer | FK | 否 | - | - |
| `author_name` | String(100) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `field` | String(100) | - | 是 | - | - |
| `from_string` | Text | - | 是 | - | - |
| `to_string` | Text | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **issue**: many-to-one → `JiraIssue`

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
| `created_at` | DateTime | - | 是 | <function JiraProject.<lambda> at 0x0000022FBDD466C0> | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **gitlab_project**: many-to-one → `Project`
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

### MergeRequest (`merge_requests`)

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

- **deployments**: one-to-many → `Deployment`
- **author**: many-to-one → `User`
- **project**: many-to-one → `Project`

---

### Milestone (`milestones`)

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

- **project**: many-to-one → `Project`
- **releases**: one-to-many → `GitLabRelease`
- **issues**: one-to-many → `Issue`

---

### NexusAsset (`nexus_assets`)

**业务描述**: Nexus 资产（文件）模型 (nexus_assets)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | String(100) | PK | 否 | - | - |
| `component_id` | String(100) | FK | 是 | - | - |
| `path` | String(500) | - | 否 | - | - |
| `download_url` | String(1000) | - | 是 | - | - |
| `size_bytes` | BigInteger | - | 是 | - | - |
| `checksum_sha1` | String(40) | - | 是 | - | - |
| `checksum_sha256` | String(64) | - | 是 | - | - |
| `checksum_md5` | String(32) | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `last_modified` | DateTime | - | 是 | - | - |
| `last_downloaded` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **component**: many-to-one → `NexusComponent`

---

### NexusComponent (`nexus_components`)

**业务描述**: Nexus 组件模型 (nexus_components)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | String(100) | PK | 否 | - | - |
| `repository` | String(100) | - | 否 | - | - |
| `format` | String(50) | - | 是 | - | - |
| `group` | String(255) | - | 是 | - | - |
| `name` | String(255) | - | 否 | - | - |
| `version` | String(100) | - | 是 | - | - |
| `product_id` | Integer | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **product**: many-to-one → `Product`
- **assets**: one-to-many → `NexusAsset`

---

### Note (`notes`)

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

- **project**: many-to-one → `Project`

---

### PerformanceRecord (`performance_records`)

**业务描述**: 性能/压力测试指标记录模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | - | 是 | - | - |
| `build_id` | String(100) | - | 是 | - | - |
| `scenario_name` | String(200) | - | 否 | - | - |
| `avg_latency` | Numeric | - | 是 | - | - |
| `p99_latency` | Numeric | - | 是 | - | - |
| `throughput` | Numeric | - | 是 | - | - |
| `error_rate` | Numeric | - | 是 | - | - |
| `concurrency` | Integer | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

---

### Pipeline (`pipelines`)

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

- **project**: many-to-one → `Project`

---

### Project (`projects`)

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
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **group**: many-to-one → `GitLabGroup`
- **organization**: many-to-one → `Organization`
- **dependency_scans**: one-to-many → `DependencyScan`
- **dependencies**: one-to-many → `Dependency`
- **milestones**: one-to-many → `Milestone`
- **members**: one-to-many → `ProjectMember`
- **commits**: one-to-many → `Commit`
- **merge_requests**: one-to-many → `MergeRequest`
- **issues**: one-to-many → `Issue`
- **pipelines**: one-to-many → `Pipeline`
- **deployments**: one-to-many → `Deployment`
- **test_cases**: one-to-many → `GTMTestCase`
- **requirements**: one-to-many → `GTMRequirement`
- **test_execution_records**: one-to-many → `GTMTestExecutionRecord`
- **sonar_projects**: one-to-many → `SonarProject`
- **jira_projects**: one-to-many → `JiraProject`

---

### RawDataStaging (`raw_data_staging`)

**业务描述**: 原始数据落盘表 (Staging Layer)。 用于存储未经转换的原始 API 响应内容。支持按需重放、审计以及故障排查。 配合生命周期管理策略，可定期清理旧数据。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `source` | String(50) | INDEX | 否 | - | - |
| `entity_type` | String(50) | INDEX | 否 | - | - |
| `external_id` | String(100) | INDEX | 否 | - | - |
| `payload` | JSON | - | 否 | - | - |
| `schema_version` | String(20) | INDEX | 是 | 1.0 | - |
| `collected_at` | DateTime | INDEX | 是 | <function RawDataStaging.<lambda> at 0x0000022FBD1C9170> | - |

---

### ResourceCost (`resource_costs`)

**业务描述**: 资源与成本流水模型。 记录各项支出的明细。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `project_id` | Integer | - | 是 | - | - |
| `product_id` | Integer | - | 是 | - | - |
| `organization_id` | String(100) | - | 是 | - | - |
| `period` | String(50) | - | 否 | - | - |
| `cost_type` | String(50) | - | 是 | - | - |
| `cost_item` | String(100) | - | 是 | - | - |
| `cost_code_id` | Integer | FK | 是 | - | - |
| `purchase_contract_id` | Integer | FK | 是 | - | - |
| `amount` | Numeric | - | 否 | - | - |
| `currency` | String(10) | - | 是 | CNY | - |
| `capex_opex_flag` | String(20) | - | 是 | - | - |
| `is_locked` | Boolean | - | 是 | False | - |
| `accounting_date` | DateTime | - | 是 | - | - |
| `source_system` | String(50) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `service_id` | Integer | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x0000022FBD1C8EB0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **cost_code**: many-to-one → `CostCode`
- **purchase_contract**: many-to-one → `PurchaseContract`
- **service**: many-to-one → `Service`

---

### ServiceProjectMapping (`service_project_mappings`)

**业务描述**: 服务与技术项目映射表。 解决一个逻辑服务对应多个代码仓库/项目的问题。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `service_id` | Integer | FK | 否 | - | - |
| `source` | String(50) | - | 是 | gitlab | - |
| `project_id` | Integer | - | 否 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x0000022FBD1C8EB0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **service**: many-to-one → `Service`

---

### SLO (`slos`)

**业务描述**: 服务等级目标模型 (SLO)。 定义服务的可靠性承诺，衡量服务是否达到预期水平。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `service_id` | Integer | FK | 否 | - | - |
| `name` | String(200) | - | 否 | - | - |
| `indicator_type` | String(50) | - | 是 | - | - |
| `target_value` | Numeric | - | 否 | - | - |
| `metric_unit` | String(20) | - | 是 | - | - |
| `time_window` | String(20) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x0000022FBD1C8EB0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **service**: many-to-one → `Service`

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
| `created_at` | DateTime | - | 是 | <function SonarMeasure.<lambda> at 0x0000022FBDCEF3D0> | - |

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
| `created_at` | DateTime | - | 是 | <function SonarProject.<lambda> at 0x0000022FBDCEE820> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **gitlab_project**: many-to-one → `Project`
- **measures**: one-to-many → `SonarMeasure`
- **issues**: one-to-many → `SonarIssue`
- **latest_measure**: many-to-one → `SonarMeasure`

---

### Tag (`tags`)

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

- **project**: many-to-one → `Project`

---

### TraceabilityLink (`traceability_links`)

**业务描述**: 通用链路追溯映射表。 支持在任意两个 DevOps 对象之间建立链接（如：Jira Issue <-> GitLab MR）。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `source_system` | String(50) | - | 否 | - | - |
| `source_type` | String(50) | - | 否 | - | - |
| `source_id` | String(100) | - | 否 | - | - |
| `target_system` | String(50) | - | 否 | - | - |
| `target_type` | String(50) | - | 否 | - | - |
| `target_id` | String(100) | - | 否 | - | - |
| `link_type` | String(50) | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x0000022FBD1C8EB0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### UserActivityProfile (`user_activity_profiles`)

**业务描述**: 用户行为画像模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `user_id` | UUID | FK | 否 | - | - |
| `period` | String(50) | - | 否 | - | - |
| `avg_review_turnaround` | Numeric | - | 是 | - | - |
| `review_participation_rate` | Numeric | - | 是 | - | - |
| `context_switch_rate` | Numeric | - | 是 | - | - |
| `contribution_diversity` | Numeric | - | 是 | - | - |
| `top_languages` | JSON | - | 是 | - | - |
| `off_hours_activity_ratio` | Numeric | - | 是 | - | - |
| `weekend_activity_count` | Integer | - | 是 | - | - |
| `avg_lint_errors_per_kloc` | Numeric | - | 是 | - | - |
| `code_review_acceptance_rate` | Numeric | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `created_at` | DateTime | - | 是 | <function TimestampMixin.<lambda> at 0x0000022FBD1C8EB0> | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **user**: many-to-one → `User`

---

### ZenTaoExecution (`zentao_executions`)

**业务描述**: 禅道执行模型 (zentao_executions)，即迭代/Sprint。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `product_id` | Integer | FK | 否 | - | - |
| `name` | String(255) | - | 是 | - | - |
| `code` | String(100) | - | 是 | - | - |
| `type` | String(20) | - | 是 | - | - |
| `status` | String(20) | - | 是 | - | - |
| `begin` | DateTime | - | 是 | - | - |
| `end` | DateTime | - | 是 | - | - |
| `real_began` | DateTime | - | 是 | - | - |
| `real_end` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **product**: many-to-one → `ZenTaoProduct`

---

### ZenTaoIssue (`zentao_issues`)

**业务描述**: 禅道 Issue 模型 (zentao_issues)，包含需求 (Story) 和 缺陷 (Bug)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `product_id` | Integer | FK | 否 | - | - |
| `execution_id` | Integer | FK | 是 | - | - |
| `plan_id` | Integer | FK | 是 | - | - |
| `title` | String(500) | - | 否 | - | - |
| `type` | String(50) | - | 是 | - | - |
| `status` | String(50) | - | 是 | - | - |
| `priority` | Integer | - | 是 | - | - |
| `opened_by` | String(100) | - | 是 | - | - |
| `assigned_to` | String(100) | - | 是 | - | - |
| `opened_by_user_id` | UUID | FK | 是 | - | - |
| `assigned_to_user_id` | UUID | FK | 是 | - | - |
| `user_id` | UUID | FK | 是 | - | - |
| `created_at` | DateTime | - | 是 | - | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `closed_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |
| `first_commit_sha` | String(100) | - | 是 | - | - |
| `first_fix_date` | DateTime | - | 是 | - | - |

#### 关系映射

- **product**: many-to-one → `ZenTaoProduct`
- **plan**: many-to-one → `ZenTaoProductPlan`

---

### ZenTaoProduct (`zentao_products`)

**业务描述**: 禅道产品模型 (zentao_products)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `name` | String(255) | - | 否 | - | - |
| `code` | String(100) | - | 是 | - | - |
| `description` | Text | - | 是 | - | - |
| `status` | String(20) | - | 是 | - | - |
| `gitlab_project_id` | Integer | FK | 是 | - | - |
| `last_synced_at` | DateTime | - | 是 | - | - |
| `sync_status` | String(20) | - | 是 | PENDING | - |
| `created_at` | DateTime | - | 是 | <function ZenTaoProduct.<lambda> at 0x0000022FBDE1D7A0> | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **executions**: one-to-many → `ZenTaoExecution`
- **plans**: one-to-many → `ZenTaoProductPlan`
- **issues**: one-to-many → `ZenTaoIssue`
- **test_cases**: one-to-many → `ZenTaoTestCase`
- **builds**: one-to-many → `ZenTaoBuild`
- **releases**: one-to-many → `ZenTaoRelease`
- **actions**: one-to-many → `ZenTaoAction`

---

## 🧠 高级数据挖掘与智能分析模型 (Advanced Analytics & Intelligence Models)

本章节描述了通过 dbt 实现的智能化分析模型，这些模型通过多维聚合和算法识别生成高价值洞察。

### 1. 统一活动流引擎 (Unified Activity Stream Engine)

- **核心逻辑**: 将 Commits, MRs, Issues, Comments 等原子操作打平为标准的、带权重的事件流。
- **价值**: 实现跨工具的统一产出度量，是画像和效能分析的母表。
- **维度**: 发生时间、操作者、操作类型、目标实体、来源系统。
- **指标**: 基础影响分 (Base Impact Score)。
- **说明**: 对不同类型的动作分配权重（如：提交=1，合并=2，评论=0.5）。
- **意义**: 解决了工具孤岛导致的数据口径不一问题。
- **实现方式**: dbt Intermediate Model (`int_unified_activities`)。
- **SQL脚本**: `dbt_project/models/intermediate/int_unified_activities.sql` (聚合产出数据流)

### 2. 模糊实体对齐与链接 (Fuzzy Entity Resolution & Linkage)

- **核心逻辑**: 基于 Levenshtein 距离及 ID 前缀匹配，自动关联 GitLab 仓库与 MDM 资产。
- **价值**: 实现技术资产与业务资产的自动化映射。
- **维度**: 映射策略 (Strategy)、对齐置信度 (Confidence)。
- **指标**: 文本相似度得分 (Similarity Score)。
- **说明**: 处理项目名称不一致但路径相似的“幽灵关联”。
- **意义**: 极大降低了人工维护资产映射表的成本。
- **实现方式**: dbt Intermediate Model -> Reverse ETL to `mdm_entities_topology`。
- **SQL脚本**: `dbt_project/models/intermediate/int_entity_alignment.sql` (实现跨系统实体自动关联)

### 3. 开发者 DNA 画像 (Developer Activity DNA Profile)

- **核心逻辑**: 基于活动流聚类算法，识别开发者的工作范式（代码机器、评审专家、需求终结者）。
- **价值**: 识别团队中的技术领袖和“胶水人”。
- **维度**: 用户、主要贡献技能、工作范式 (Archetype)。
- **指标**: 活跃重心分、交付频率。
- **说明**: 通过分析 MR 评论数 vs 代码提交数的比率来判定画像。
- **意义**: 辅助 HR 进行人才盘点和技术骨干识别。
- **实现方式**: dbt Mart Model (`fct_developer_activity_profile`)。
- **SQL脚本**: `dbt_project/models/marts/fct_developer_activity_profile.sql` (生成开发者技术基因画像)

### 4. 研发投入资本化审计 (Capitalization Audit)

- **核心逻辑**: 通过 Issue 标签 -> MR -> Commits 的穿透关联，核算归属于 CapEx 的实际工作量。
- **价值**: 为财务资产化提供不可篡改的代码级审计依据。
- **维度**: Epic, Portfolio Link, 审计状态 (Audit Status)。
- **指标**: 审计工作量单位 (Audit Effort Units/Commits)。
- **说明**: 关联 Epic 到具体的物理代码变更。
- **意义**: 确保 R&D 资本化合规，满足外部审计要求。
- **实现方式**: dbt Mart Model (`fct_capitalization_audit`)。
- **SQL脚本**: `dbt_project/models/marts/fct_capitalization_audit.sql` (提供研发成本资本化审计链路)

### 5. 交付成本与 FinOps 桥接 (Delivery Costs / FinOps Bridge)

- **核心逻辑**: 将开发者活动时长乘以 MDM 维护的标准费率 (Labor Rates)，生成项目/服务级成本。
- **价值**: 实现研发投入的可视化，识别高成本低产出区域。
- **维度**: 服务 ID、成本中心。
- **指标**: 累计研发投入成本 (Total Labor Cost)。
- **说明**: 结合 `mdm_resource_costs` 实现动态成本核算。
- **意义**: 为项目投资回报率 (ROI) 提供实时反馈。
- **实现方式**: dbt Mart Model (`fct_delivery_costs`)。
- **SQL脚本**: `dbt_project/models/marts/fct_delivery_costs.sql` (将工程动作转化为财务价值)

### 6. 指标一致性哨兵 (Metrics Consistency Guard)

- **核心逻辑**: 利用统计学指纹和 3-Sigma 离群值检测，识别异常波动或人为造假的指标。
- **价值**: 确保 DORA 等关键指标的真实性，防止指标驱动开发导致的“刷分”。
- **维度**: 检查时间项、异常类型。
- **指标**: 离群值标志 (Is Outlier)。
- **说明**: 监控超短 Lead Time 等不合逻辑的数据。
- **意义**: 建立数据信用体系，防止管理误导。
- **实现方式**: dbt Mart Model (`fct_metrics_audit_guard`)。
- **SQL脚本**: `dbt_project/models/marts/fct_metrics_audit_guard.sql` (指标异常自动检测)

### 7. 影子系统发现 (Shadow IT Discovery)

- **核心逻辑**: 通过活跃 Repo 与 MDM 注册资产的差集识别“黑产”或非合规项目。
- **价值**: 消除治理盲区。
- **维度**: 项目、活跃度状态 (Shadow IT Status)。
- **指标**: 最近 30d 动作数。
- **说明**: 自动识别活跃但未进入 MDM 纳管的项目。
- **意义**: 降低安全和合规性风险。
- **实现方式**: dbt Mart Model (`fct_shadow_it_discovery`)。
- **SQL脚本**: `dbt_project/models/marts/fct_shadow_it_discovery.sql` (发现未注册的影子资产)

### 8. DORA 核心度量 (DORA Metrics)

- **核心逻辑**: 依照 DevOps 标准度量模型，聚合产出发布频率、Lead Time、失败率等指标。
- **价值**: 提供跨部门统一的效能对标基准。
- **维度**: 项目、月份。
- **指标**: Deployment Frequency, Lead Time, Change Failure Rate, MTTR。
- **说明**: 全球通用的 DevOps 效能衡量金标准。
- **意义**: 指导团队持续改进交付流程。
- **实现方式**: dbt Mart Model (`fct_dora_metrics`)。
- **SQL脚本**: `dbt_project/models/marts/fct_dora_metrics.sql` (标准化 DORA 指标计算)

### 9. 项目交付健康度 360 (Project Delivery Health 360)

- **核心逻辑**: 结合代码分布、扫描风险、MR 积压及测试覆盖率生成的加权分。
- **价值**: 实现项目健康度的“红绿灯”监控。
- **维度**: 质量等级、构建状态。
- **指标**: 综合健康分 (Health Score)。
- **说明**: 多位一体的项目实时健康监视器。
- **意义**: 帮助管理者快速定位高风险项目。
- **实现方式**: dbt Mart Model (`fct_project_delivery_health`)。
- **SQL脚本**: `dbt_project/models/marts/fct_project_delivery_health.sql` (动态计算项目多维健康度)

### 10. 合规与内控审计 (Governance & Compliance Audit)

- **核心逻辑**: 识别“绕过评审合并”和“直连推送”等违规操作记录。
- **价值**: 提供不可篡改的变更管理合规存证。
- **维度**: 合规状态、分支保护项。
- **指标**: Suspicious Bypass Rate.
- **说明**: 针对 SOX 404 四眼原则进行自动化审计。
- **意义**: 降低审计成本，确保流程合规执行。
- **实现方式**: dbt Mart Model (`fct_compliance_audit`)。
- **SQL脚本**: `dbt_project/models/marts/fct_compliance_audit.sql` (自动化识别流程规避行为)

### 11. 架构脆性指数 (Architectural Brittleness Index)

- **核心逻辑**: 通过包引用的 In-Degree 高度关联技术债务与低覆盖率。
- **价值**: 预测核心组件的崩溃风险。
- **维度**: 架构状态 (Architectural Status)。
- **指标**: ABI Score.
- **说明**: 识别那“大影响面、高质量债”的核心黑盒模块。
- **意义**: 指导架构重构的优先级建议。
- **实现方式**: dbt Mart Model (`fct_architectural_brittleness`)。
- **SQL脚本**: `dbt_project/models/marts/fct_architectural_brittleness.sql` (量化核心模块的架构坍塌风险)

### 12. 人才雷达识别 (Talent Radar)

- **核心逻辑**: 综合多维贡献度（代码、评审、文档）进行技术影响力排名。
- **价值**: 自动发现组织内的 Top 1% 金牌开发者。
- **维度**: 用户、部门、技能标签。
- **指标**: 影响力综合得分 (Influence Score)。
- **说明**: 配合 `fct_developer_activity_profile` 提供更深入的人才洞察。
- **意义**: 辅助组织绩效评价与继任者计划。
- **实现方式**: dbt Mart Model (`fct_talent_radar`)。
- **SQL脚本**: `dbt_project/models/marts/fct_talent_radar.sql` (构建组织内的高级技术人才塔)

### 13. 统一扁平化工作项引擎 (Unified Flattened Work Items)

- **核心逻辑**: 消除 Jira 与 GitLab 需求/任务的字段差异，映射到统一工作流。
- **价值**: 跨工具流转透明化。
- **维度**: 系统、优先级、到期日。
- **指标**: 交付偏差率 (TV)。
- **说明**: 业务视角的“大一统”任务池。
- **意义**: 解决了跨部门协作中“不同工具不同语言”的沟通壁垒。
- **实现方式**: dbt Intermediate Model (`int_unified_work_items`)。
- **SQL脚本**: `dbt_project/models/intermediate/int_unified_work_items.sql` (实现全渠道工作项对齐)

---

### v3.0 (2026-01-04)

- ✅ 引入 **dbt 数据质量哨兵 (Data Quality Sentinel)** 架构
- ✅ 为核心源表 (`mdm_identities`, `gitlab_projects` 等) 部署 Schema 测试
- ✅ 实现了关键聚合逻辑的 **dbt 单元测试 (Unit Testing)** 覆盖
- ✅ 新增 **业务一致性审计测试 (`assert_developer_count_consistency`)**

### v2.1 (2026-01-01)

- ✅ 新增 **dbt 智能分析模型** 章节，涵盖 DORA、ABI、DNA 画像等高级逻辑
- ✅ 新增 **影子系统发现** 与 **指标审计哨兵** 模型描述
- ✅ 完善了各个模型的核心逻辑、指标及价值说明
- ✅ 统一了 dbt Marts 脚本的存放位置记录

### v2.0 (2025-12-28)

- ✅ 基于最新 SQLAlchemy 模型自动生成
- ✅ 新增企业级分域架构组织
- ✅ 完善字段约束和关系映射说明
- ⚠️  废弃旧版数据字典 (已归档至 `DATA_DICTIONARY_DEPRECATED_20251228.md`)

---

**维护说明**: 本文档由 `scripts/generate_data_dictionary.py` 自动生成，请勿手动编辑！如需更新，请修改模型定义并重新运行生成脚本。

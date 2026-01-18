# DevOps 效能平台 - 数据字典 (Data Dictionary)

> **生成时间**: 2026-01-18 13:29:15  
> **版本**: v2.2 (企业级标准版)  
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

### 字段注释规范
- 所有新增字段必须在模型定义中使用 `comment` 参数添加业务说明
- 枚举类型字段需列出所有可选值
- 外键字段需说明关联的业务实体

---

## 数据表清单

本系统共包含 **72 个数据表**，分为以下几个业务域：


### 核心主数据域
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

### 测试管理域
- `gtm_requirements` - GTMRequirement
- `gtm_test_case_issue_links` - GTMTestCaseIssueLink
- `gtm_test_cases` - GTMTestCase
- `gtm_test_execution_records` - GTMTestExecutionRecord
- `jenkins_test_executions` - JenkinsTestExecution

### GitLab 集成域
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

### 认证与授权域
- `sys_user_credentials` - UserCredential
- `sys_user_oauth_tokens` - UserOAuthToken
- `sys_user_roles` - UserRole

### 其他辅助域
- `commit_metrics` - CommitMetrics
- `daily_dev_stats` - DailyDevStats
- `dependencies` - Dependency
- `dependency_cves` - DependencyCVE
- `dependency_scans` - DependencyScan
- `jira_boards` - JiraBoard
- `jira_issues` - JiraIssue
- `jira_projects` - JiraProject
- `jira_sprints` - JiraSprint
- `license_risk_rules` - LicenseRiskRule
- `sonar_issues` - SonarIssue
- `sonar_measures` - SonarMeasure
- `sonar_projects` - SonarProject
- `stg_raw_data` - RawDataStaging
- `sys_menu` - SysMenu
- `sys_role` - SysRole
- `sys_role_dept` - SysRoleDept
- `sys_role_menu` - SysRoleMenu
- `sys_sync_logs` - SyncLog
- `sys_team_members` - TeamMember
- `sys_teams` - Team

---

## 核心主数据域

### Calendar (`mdm_calendar`)

**业务描述**: 公共日历/节假日参考表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `date_day` | Date | UNIQUE, INDEX | 否 | - | 日期 |
| `year_number` | Integer | INDEX | 是 | - | 年份 |
| `month_number` | Integer | - | 是 | - | 月份 (1-12) |
| `quarter_number` | Integer | - | 是 | - | 季度 (1-4) |
| `day_of_week` | Integer | - | 是 | - | 星期几 (1=周一, 7=周日) |
| `is_workday` | Boolean | - | 是 | True | 是否工作日 |
| `is_holiday` | Boolean | - | 是 | False | 是否节假日 |
| `holiday_name` | String(100) | - | 是 | - | 节假日名称 |
| `fiscal_year` | String(20) | - | 是 | - | 财年 |
| `fiscal_quarter` | String(20) | - | 是 | - | 财务季度 |
| `week_of_year` | Integer | - | 是 | - | 年内周数 |
| `season_tag` | String(20) | - | 是 | - | 季节标签 (春/夏/秋/冬) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### Company (`mdm_company`)

**业务描述**: 公司实体参考表 (Legal Entity)。 用于定义集团内的法律实体/纳税主体，支持财务核算和合同签署主体的管理。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `company_id` | String(50) | PK | 否 | - | 公司唯一标识 (如 COM-BJ-01) |
| `name` | String(200) | - | 否 | - | 公司注册全称 |
| `short_name` | String(100) | - | 是 | - | 公司简称 |
| `tax_id` | String(50) | UNIQUE, INDEX | 是 | - | 统一社会信用代码/税号 |
| `currency` | String(10) | - | 是 | CNY | 本位币种 (CNY/USD) |
| `fiscal_year_start` | String(10) | - | 是 | 01-01 | 财年开始日期 (MM-DD) |
| `registered_address` | String(255) | - | 是 | - | 注册地址 |
| `location_id` | String(50) | FK | 是 | - | 主要办公地点ID |
| `is_active` | Boolean | - | 是 | True | 是否存续经营 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **location**: many-to-one -> `Location`

---

### ComplianceIssue (`mdm_compliance_issues`)

**业务描述**: 合规风险与审计问题记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `issue_type` | String(50) | - | 是 | - | 问题类型 (安全漏洞/许可证违规/合规缺失) |
| `severity` | String(20) | - | 是 | - | 严重等级 (Critical/High/Medium/Low) |
| `entity_id` | String(100) | INDEX | 是 | - | 关联实体ID (项目/服务) |
| `status` | String(20) | - | 是 | OPEN | 状态 (OPEN/IN_REVIEW/RESOLVED/ACCEPTED) |
| `description` | Text | - | 是 | - | 问题详情 |
| `metadata_payload` | JSON | - | 是 | - | 额外元数据 (JSON) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### ContractPaymentNode (`mdm_contract_payment_nodes`)

**业务描述**: 合同付款节点/收款计划记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `contract_id` | Integer | FK | 否 | - | 关联合同ID |
| `node_name` | String(200) | - | 否 | - | 节点名称 |
| `billing_percentage` | Numeric | - | 是 | - | 收款比例 (%) |
| `billing_amount` | Numeric | - | 是 | - | 收款金额 |
| `linked_system` | String(50) | - | 是 | - | 关联系统 (gitlab/jira/manual) |
| `linked_milestone_id` | Integer | - | 是 | - | 关联里程碑ID |
| `is_achieved` | Boolean | - | 是 | False | 是否已达成 |
| `achieved_at` | DateTime | - | 是 | - | 达成时间 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **contract**: many-to-one -> `RevenueContract`

---

### CostCode (`mdm_cost_codes`)

**业务描述**: 成本科目 (CBS) 模型。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `code` | String(50) | UNIQUE, INDEX | 否 | - | 科目编码 |
| `name` | String(200) | - | 否 | - | 科目名称 |
| `category` | String(50) | - | 是 | - | 科目分类 (人力/硬件/软件/服务) |
| `description` | Text | - | 是 | - | 科目描述 |
| `parent_id` | Integer | FK | 是 | - | 上级科目ID |
| `default_capex_opex` | String(10) | - | 是 | - | 默认CAPEX/OPEX属性 |
| `is_active` | Boolean | - | 是 | True | 是否启用 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **parent**: many-to-one -> `CostCode`
- **children**: one-to-many -> `CostCode`

---

### EntityTopology (`mdm_entity_topology`)

**业务描述**: 实体-资源映射表 (Infrastructure Mapping). 将逻辑上的业务服务 (Service) 绑定到物理上的基础设施资源 (GitLab Repo, Sonar Project, Jenkins Job)。 它是连接 "业务架构" (Service) 与 "工具设施" (SystemRegistry) 的胶水层。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `service_id` | Integer | FK, INDEX | 否 | - | 所属业务服务ID |
| `system_code` | String(50) | FK | 否 | - | 来源系统代码 (如 gitlab-corp) |
| `external_resource_id` | String(100) | - | 否 | - | 外部资源唯一标识 (如 Project ID, Repo URL) |
| `resource_name` | String(200) | - | 是 | - | 资源显示名称快照 (如 backend/payment-service) |
| `env_tag` | String(20) | - | 是 | PROD | 环境标签 (PROD/UAT/TEST/DEV) |
| `element_type` | String(50) | - | 是 | source-code | 资源类型 (source-code/ci-pipeline/k8s-deployment/db-instance) |
| `is_active` | Boolean | - | 是 | True | 关联是否有效 |
| `last_verified_at` | DateTime | - | 是 | - | 最后一次验证连接有效的时间 |
| `meta_info` | JSON | - | 是 | - | 额外元数据连接信息 (JSON, 如 webhook_id, bind_key) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | (auto) | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **service**: many-to-one -> `Service`
- **target_system**: many-to-one -> `SystemRegistry`

---

### EpicMaster (`mdm_epic`)

**业务描述**: 跨团队/长期史诗需求 (Epic) 主数据。 用于管理跨越多个迭代、涉及多个团队的战略级需求组件 (Initiatives/Epics)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `parent_id` | Integer | FK | 是 | - | 父级 Epic ID (支持多层级) |
| `epic_code` | String(50) | UNIQUE, INDEX | 否 | - | 史诗唯一编码 (如 EPIC-24Q1-001) |
| `title` | String(200) | - | 否 | - | 史诗标题 |
| `description` | Text | - | 是 | - | 价值陈述与详细描述 |
| `status` | String(50) | - | 是 | ANALYSIS | 状态 (ANALYSIS/BACKLOG/IN_PROGRESS/DONE/CANCELLED) |
| `priority` | String(20) | - | 是 | P1 | 优先级 (P0-Strategic / P1-High) |
| `okr_objective_id` | Integer | FK | 是 | - | 关联战略目标ID |
| `investment_theme` | String(100) | - | 是 | - | 投资主题 (如 技术债/新业务/合规/客户体验) |
| `budget_cap` | Numeric | - | 是 | - | 预算上限 (人天或金额) |
| `owner_id` | UUID | FK | 是 | - | 史诗负责人ID (Epic Owner) |
| `group_id` | String(100) | FK | 是 | - | 所属群组/组织ID (GitLab Group) |
| `start_date_is_fixed` | Boolean | - | 是 | False | 是否固定开始时间 (False则自动继承子任务) |
| `due_date_is_fixed` | Boolean | - | 是 | False | 是否固定结束时间 |
| `planned_start_date` | Date | - | 是 | - | 计划开始日期 |
| `planned_end_date` | Date | - | 是 | - | 计划完成日期 |
| `actual_start_date` | Date | - | 是 | - | 实际开始日期 |
| `actual_end_date` | Date | - | 是 | - | 实际完成日期 |
| `progress` | Numeric | - | 是 | 0.0 | 总体进度 (0.0-1.0, 基于子任务聚合) |
| `color` | String(20) | - | 是 | - | Roadmap展示颜色 (Hex Code) |
| `is_confidential` | Boolean | - | 是 | False | 是否机密 Epic |
| `web_url` | String(255) | - | 是 | - | GitLab 原始链接 |
| `external_id` | String(50) | - | 是 | - | 外部系统ID (如 GitLab Epic IID) |
| `involved_teams` | JSON | - | 是 | - | 涉及团队列表 (JSON List) |
| `tags` | JSON | - | 是 | - | 标签 (JSON List) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **owner**: many-to-one -> `User`
- **group**: many-to-one -> `Organization`
- **okr_objective**: many-to-one -> `OKRObjective`
- **parent**: many-to-one -> `EpicMaster`
- **children**: one-to-many -> `EpicMaster`

---

### User (`mdm_identities`)

**业务描述**: 全局用户映射表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `global_user_id` | UUID | PK | 否 | (auto) | 全局唯一用户标识 |
| `employee_id` | String(50) | UNIQUE, INDEX | 是 | - | HR系统工号 |
| `username` | String(100) | - | 是 | - | 登录用户名 |
| `full_name` | String(200) | - | 是 | - | 用户姓名 |
| `primary_email` | String(255) | UNIQUE, INDEX | 是 | - | 主邮箱地址 |
| `department_id` | String(100) | FK | 是 | - | 所属部门ID |
| `position` | String(100) | - | 是 | - | 职位/岗位名称 |
| `is_active` | Boolean | - | 是 | True | 是否在职 |
| `is_survivor` | Boolean | - | 是 | False | 是否通过合并保留的账号 |
| `total_eloc` | Numeric | - | 是 | 0.0 | 累计有效代码行数 |
| `eloc_rank` | Integer | - | 是 | 0 | ELOC排名 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | (auto) | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **department**: many-to-one -> `Organization`
- **managed_organizations**: one-to-many -> `Organization`
- **identities**: one-to-many -> `IdentityMapping`
- **roles**: one-to-many -> `SysRole`
- **test_cases**: one-to-many -> `GTMTestCase`
- **requirements**: one-to-many -> `GTMRequirement`
- **managed_products_as_pm**: one-to-many -> `Product`
- **managed_products_as_dev**: one-to-many -> `Product`
- **managed_products_as_qa**: one-to-many -> `Product`
- **managed_products_as_release**: one-to-many -> `Product`
- **project_memberships**: one-to-many -> `GitLabProjectMember`
- **team_memberships**: one-to-many -> `TeamMember`
- **credential**: many-to-one -> `UserCredential`

---

### IdentityMapping (`mdm_identity_mappings`)

**业务描述**: 外部身份映射表，连接 MDM 用户与第三方系统账号。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `global_user_id` | UUID | FK, INDEX | 是 | - | 全局用户ID |
| `source_system` | String(50) | INDEX | 否 | - | 来源系统 (gitlab/jira/sonar) |
| `external_user_id` | String(100) | - | 否 | - | 外部系统用户ID |
| `external_username` | String(100) | - | 是 | - | 外部系统用户名 |
| `external_email` | String(100) | - | 是 | - | 外部系统邮箱 |
| `mapping_status` | String(20) | - | 是 | VERIFIED | 映射状态 (VERIFIED/PENDING/REJECTED) |
| `confidence_score` | Numeric | - | 是 | 1.0 | 匹配置信度 (0.0-1.0) |
| `last_active_at` | DateTime | - | 是 | - | 最后活跃时间 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **user**: many-to-one -> `User`

---

### Incident (`mdm_incidents`)

**业务描述**: 线上事故/线上问题记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `title` | String(200) | - | 否 | - | 事故标题 |
| `description` | Text | - | 是 | - | 事故详细描述 |
| `severity` | String(20) | - | 是 | - | 严重等级 (P0/P1/P2/P3) |
| `status` | String(20) | - | 是 | OPEN | 状态 (OPEN:处理中 / RESOLVED:已恢复 / CLOSED:已结单 / MONITORING:观察中) |
| `occurred_at` | DateTime | - | 是 | - | 故障发生时间 (用于计算 TTI: Time to Impact) |
| `detected_at` | DateTime | - | 是 | - | 故障发现时间 (用于计算 MTTD: Time to Detect) |
| `resolved_at` | DateTime | - | 是 | - | 业务恢复时间 (用于计算 MTTR: Time to Restore) |
| `location_id` | String(50) | FK | 是 | - | 故障发生地点ID |
| `root_cause_category` | String(50) | - | 是 | - | 根因分类 (Code Change/Config Change/Capacity/Infrastructure/Exteanl) |
| `post_mortem_url` | String(255) | - | 是 | - | 复盘报告链接 (Confluence/Doc URL) |
| `affected_users` | Integer | - | 是 | - | 受影响用户数量预估 |
| `financial_loss` | Numeric | - | 是 | 0.0 | 预估经济损失金额 (CNY) |
| `owner_id` | UUID | FK | 是 | - | 主责任人ID (On-call) |
| `project_id` | String(100) | FK | 是 | - | 关联项目ID |
| `service_id` | Integer | FK | 是 | - | 故障服务ID |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **location**: many-to-one -> `Location`
- **owner**: many-to-one -> `User`
- **project**: many-to-one -> `ProjectMaster`
- **service**: many-to-one -> `Service`

---

### LaborRateConfig (`mdm_labor_rate_config`)

**业务描述**: 人工标准费率配置表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `job_title_level` | String(50) | - | 否 | - | 职级 (P5/P6/P7/M1/M2) |
| `daily_rate` | Numeric | - | 否 | - | 日费率 (元) |
| `hourly_rate` | Numeric | - | 是 | - | 时费率 (元) |
| `currency` | String(10) | - | 是 | CNY | 币种 |
| `effective_date` | DateTime | - | 是 | - | 生效日期 |
| `is_active` | Boolean | - | 是 | True | 是否启用 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### Location (`mdm_locations`)

**业务描述**: 地理位置或机房位置参考表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `location_id` | String(50) | UNIQUE, INDEX | 是 | - | 位置唯一标识 (如 UUID) |
| `code` | String(20) | UNIQUE, INDEX | 是 | - | 行政区划或业务编码 (如 CN-GD, 440000) |
| `location_name` | String(200) | - | 否 | - | 位置名称 (如 广东省) |
| `short_name` | String(50) | - | 是 | - | 简称 (如 广东) |
| `location_type` | String(50) | - | 是 | - | 位置类型 (country/province/city/site/datacenter) |
| `parent_id` | String(50) | - | 是 | - | 上级位置ID |
| `region` | String(50) | - | 是 | - | 区域 (华北/华东/华南) |
| `is_active` | Boolean | - | 是 | True | 是否启用 |
| `manager_user_id` | UUID | FK | 是 | - | 负责人ID |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### MetricDefinition (`mdm_metric_definitions`)

**业务描述**: 指标语义定义表 (mdm_metric_definitions)。 这是 "指标字典" 的核心，确保全集团计算逻辑一致 (Single Source of Truth)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `metric_code` | String(100) | PK | 否 | - | 指标唯一编码 (如 DORA_MTTR_PROD) |
| `metric_name` | String(200) | - | 否 | - | 指标展示名称 (如 生产环境平均修复时间) |
| `domain` | String(50) | - | 否 | - | 所属业务域 (DEVOPS/FINANCE/OPERATION) |
| `metric_type` | String(50) | - | 是 | - | 指标类型 (ATOMIC:原子指标 / DERIVED:派生指标 / COMPOSITE:复合指标) |
| `calculation_logic` | Text | - | 是 | - | 计算逻辑说明 (SQL公式或自然语言描述) |
| `unit` | String(50) | - | 是 | - | 度量单位 (%, ms, Hours, Count, CNY) |
| `aggregate_type` | String(20) | - | 是 | - | 聚合方式 (SUM, AVG, COUNT, MAX, MIN) |
| `source_model` | String(200) | - | 是 | - | 来源数据模型 (关联 dbt 模型或数据库表名) |
| `dimension_scope` | JSON | - | 是 | - | 允许下钻的维度列表 (JSON List, 如 ["dept", "application", "priority"]) |
| `is_standard` | Boolean | - | 是 | True | 是否集团标准指标 (True: 锁定口径, 不允许随意修改) |
| `business_owner_id` | UUID | FK | 是 | - | 指标业务负责人ID (PDM/Data Owner) |
| `time_grain` | String(50) | - | 是 | - | 统计时间粒度 (Daily, Weekly, Monthly) |
| `update_cycle` | String(50) | - | 是 | - | 数据刷新周期 (Realtime, T+1, Hourly) |
| `status` | String(50) | - | 是 | RELEASED | 生命周期状态 (DRAFT:草稿 / RELEASED:已发布 / DEPRECATED:已废弃) |
| `is_active` | Boolean | - | 是 | True | 是否启用 (逻辑删除标志) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **business_owner**: many-to-one -> `User`

---

### OKRKeyResult (`mdm_okr_key_results`)

**业务描述**: OKR 关键结果 (KR) 定义表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `objective_id` | Integer | FK | 否 | - | 关联目标ID |
| `title` | String(255) | - | 否 | - | KR标题 |
| `target_value` | Numeric | - | 否 | - | 目标值 |
| `current_value` | Numeric | - | 是 | 0.0 | 当前值 |
| `unit` | String(20) | - | 是 | - | 单位 (%/天/个) |
| `weight` | Numeric | - | 是 | 1.0 | 权重 |
| `owner_id` | UUID | FK | 是 | - | 负责人ID |
| `progress` | Numeric | - | 是 | 0.0 | 进度 (0.0-1.0) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **objective**: many-to-one -> `OKRObjective`
- **owner**: many-to-one -> `User`

---

### OKRObjective (`mdm_okr_objectives`)

**业务描述**: OKR 目标定义表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `objective_id` | String(50) | UNIQUE, INDEX | 是 | - | 目标唯一标识 |
| `title` | String(255) | - | 否 | - | 目标标题 |
| `description` | Text | - | 是 | - | 目标描述 |
| `period` | String(20) | INDEX | 是 | - | 周期 (2024-Q1/2024-H1) |
| `owner_id` | UUID | FK | 是 | - | 负责人ID |
| `org_id` | String(100) | FK | 是 | - | 所属组织ID |
| `status` | String(20) | - | 是 | ACTIVE | 状态 (ACTIVE/COMPLETED/ABANDONED) |
| `progress` | Numeric | - | 是 | 0.0 | 进度 (0.0-1.0) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **owner**: many-to-one -> `User`
- **organization**: many-to-one -> `Organization`
- **key_results**: one-to-many -> `OKRKeyResult`

---

### Organization (`mdm_organizations`)

**业务描述**: 组织架构表，支持 SCD Type 2 生命周期管理。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `org_id` | String(100) | UNIQUE, INDEX | 否 | - | 组织唯一标识 (HR系统同步) |
| `org_name` | String(200) | - | 否 | - | 组织名称 |
| `org_level` | Integer | - | 是 | 1 | 组织层级 (1=公司, 2=部门, 3=团队) |
| `parent_org_id` | String(100) | FK | 是 | - | 上级组织ID |
| `manager_user_id` | UUID | FK | 是 | - | 部门负责人用户ID |
| `is_active` | Boolean | - | 是 | True | 是否启用 |
| `cost_center` | String(100) | - | 是 | - | 成本中心编码 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | (auto) | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **parent**: many-to-one -> `Organization`
- **manager**: many-to-one -> `User`
- **users**: one-to-many -> `User`
- **products**: one-to-many -> `Product`
- **gitlab_projects**: one-to-many -> `GitLabProject`
- **children**: one-to-many -> `Organization`
- **roles**: one-to-many -> `SysRole`

---

### Product (`mdm_product`)

**业务描述**: 产品主数据表 (mdm_product)。 支持 SCD Type 2，记录产品生命周期状态、负责人变更及规格调整的历史轨迹。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `product_id` | String(100) | PK | 否 | - | 产品唯一标识 |
| `product_code` | String(25) | INDEX | 否 | - | 产品编码 |
| `product_name` | String(255) | - | 否 | - | 产品名称 |
| `product_description` | Text | - | 否 | - | 产品描述 |
| `category` | String(100) | - | 是 | - | 产品分类 (平台/应用/组件) |
| `version_schema` | String(50) | - | 否 | - | 版本命名规则 (SemVer/CalVer) |
| `specification` | JSON | - | 是 | - | 产品规格配置 (JSON) |
| `runtime_env` | JSON | - | 是 | - | 运行环境配置 (JSON) |
| `checksum` | String(255) | - | 是 | - | 最新版本校验码 |
| `lifecycle_status` | String(50) | - | 是 | Active | 生命周期状态 (Active/Deprecated/EOL) |
| `repo_url` | String(255) | - | 是 | - | 主代码仓库URL |
| `artifact_path` | String(255) | - | 是 | - | 制品存储路径 |
| `owner_team_id` | String(100) | FK | 是 | - | 负责团队ID |
| `product_manager_id` | UUID | FK | 是 | - | 产品经理ID |
| `dev_lead_id` | UUID | FK | 是 | - | 开发负责人ID |
| `qa_lead_id` | UUID | FK | 是 | - | 测试负责人ID |
| `release_lead_id` | UUID | FK | 是 | - | 发布负责人ID |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | (auto) | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **owner_team**: many-to-one -> `Organization`
- **product_manager**: many-to-one -> `User`
- **dev_lead**: many-to-one -> `User`
- **qa_lead**: many-to-one -> `User`
- **release_lead**: many-to-one -> `User`
- **project_relations**: one-to-many -> `ProjectProductRelation`

---

### ProjectMaster (`mdm_projects`)

**业务描述**: 项目全生命周期主数据 (mdm_projects)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `project_id` | String(100) | PK | 否 | - | 项目唯一标识 |
| `project_name` | String(200) | - | 否 | - | 项目名称 |
| `project_type` | String(50) | - | 是 | - | 项目类型 (研发项目/运维项目/POC) |
| `status` | String(50) | - | 是 | PLAN | 项目状态 (PLAN/ACTIVE/SUSPENDED/CLOSED) |
| `is_active` | Boolean | - | 是 | True | 是否启用 |
| `pm_user_id` | UUID | FK | 是 | - | 项目经理ID |
| `product_owner_id` | UUID | FK | 是 | - | 产品负责人ID |
| `dev_lead_id` | UUID | FK | 是 | - | 开发负责人ID |
| `qa_lead_id` | UUID | FK | 是 | - | 测试负责人ID |
| `release_lead_id` | UUID | FK | 是 | - | 发布负责人ID |
| `org_id` | String(100) | FK | 是 | - | 负责部门ID |
| `location_id` | String(50) | FK | 是 | - | 项目所属/实施地点ID |
| `plan_start_date` | Date | - | 是 | - | 计划开始日期 |
| `plan_end_date` | Date | - | 是 | - | 计划结束日期 |
| `actual_start_at` | DateTime | - | 是 | - | 实际开始时间 |
| `actual_end_at` | DateTime | - | 是 | - | 实际结束时间 |
| `external_id` | String(100) | UNIQUE | 是 | - | 外部系统项目ID |
| `system_code` | String(50) | FK | 是 | - | 数据来源系统 |
| `budget_code` | String(100) | - | 是 | - | 预算编码 |
| `budget_type` | String(50) | - | 是 | - | 预算类型 (CAPEX/OPEX) |
| `lead_repo_id` | Integer | - | 是 | - | 主代码仓库ID |
| `description` | Text | - | 是 | - | 项目描述 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | (auto) | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **organization**: many-to-one -> `Organization`
- **project_manager**: many-to-one -> `User`
- **product_owner**: many-to-one -> `User`
- **dev_lead**: many-to-one -> `User`
- **qa_lead**: many-to-one -> `User`
- **release_lead**: many-to-one -> `User`
- **source_system**: many-to-one -> `SystemRegistry`
- **gitlab_repos**: one-to-many -> `GitLabProject`
- **product_relations**: one-to-many -> `ProjectProductRelation`

---

### PurchaseContract (`mdm_purchase_contracts`)

**业务描述**: 采购/支出合同主数据。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `contract_no` | String(100) | UNIQUE, INDEX | 否 | - | 合同编号 |
| `title` | String(255) | - | 是 | - | 合同标题 |
| `vendor_name` | String(255) | - | 是 | - | 供应商名称 |
| `vendor_id` | String(100) | - | 是 | - | 供应商ID |
| `total_amount` | Numeric | - | 是 | 0.0 | 合同总额 |
| `currency` | String(10) | - | 是 | CNY | 币种 |
| `start_date` | Date | - | 是 | - | 合同开始日期 |
| `end_date` | Date | - | 是 | - | 合同结束日期 |
| `cost_code_id` | Integer | FK | 是 | - | 成本科目ID |
| `capex_opex_flag` | String(10) | - | 是 | - | CAPEX/OPEX标志 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **cost_code**: many-to-one -> `CostCode`

---

### ProjectProductRelation (`mdm_rel_project_product`)

**业务描述**: 项目与产品的关联权重表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `project_id` | String(100) | FK, INDEX | 否 | - | 项目ID |
| `org_id` | String(100) | INDEX | 否 | - | 所属组织ID |
| `product_id` | String(100) | FK, INDEX | 否 | - | 产品ID |
| `relation_type` | String(50) | - | 是 | PRIMARY | 关联类型 (PRIMARY/SECONDARY) |
| `allocation_ratio` | Numeric | - | 是 | 1.0 | 工作量分配比例 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one -> `ProjectMaster`
- **product**: many-to-one -> `Product`

---

### RevenueContract (`mdm_revenue_contracts`)

**业务描述**: 销售/收入合同主数据表格。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `contract_no` | String(100) | UNIQUE, INDEX | 否 | - | 合同编号 |
| `title` | String(255) | - | 是 | - | 合同标题 |
| `client_name` | String(255) | - | 是 | - | 客户名称 |
| `total_value` | Numeric | - | 是 | 0.0 | 合同总额 |
| `currency` | String(10) | - | 是 | CNY | 币种 |
| `sign_date` | Date | - | 是 | - | 签约日期 |
| `product_id` | String(100) | FK | 是 | - | 关联产品ID |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **product**: many-to-one -> `Product`
- **payment_nodes**: one-to-many -> `ContractPaymentNode`

---

### ServiceProjectMapping (`mdm_service_project_mapping`)

**业务描述**: 服务与工程项目的多对多关联映射表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `service_id` | Integer | FK | 否 | - | 服务ID |
| `source` | String(50) | - | 是 | - | 项目来源系统 (gitlab/jira) |
| `project_id` | Integer | - | 是 | - | 外部项目ID |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **service**: many-to-one -> `Service`

---

### Service (`mdm_services`)

**业务描述**: 服务/组件目录表 (Extended with Backstage Component Model). 支持 SCD Type 2，记录服务定级 (Tier)、生命周期 (Lifecycle) 及归属权的历史演进。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `name` | String(200) | - | 否 | - | 服务名称 |
| `tier` | String(20) | - | 是 | - | 服务级别 (T0/T1/T2/T3) |
| `org_id` | String(100) | FK | 是 | - | 负责组织ID |
| `description` | Text | - | 是 | - | 服务描述 |
| `system_id` | Integer | FK | 是 | - | 所属业务系统ID |
| `lifecycle` | String(20) | - | 是 | production | 生命周期 (experimental/production/deprecated) |
| `component_type` | String(20) | - | 是 | service | 组件类型 (service/library/website/tool) |
| `tags` | JSON | - | 是 | - | 标签列表 (JSON) |
| `links` | JSON | - | 是 | - | 相关链接 (JSON) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | (auto) | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **system**: many-to-one -> `BusinessSystem`
- **organization**: many-to-one -> `Organization`
- **costs**: one-to-many -> `ResourceCost`
- **slos**: one-to-many -> `SLO`
- **project_mappings**: one-to-many -> `ServiceProjectMapping`
- **resources**: one-to-many -> `EntityTopology`

---

### SLO (`mdm_slo_definitions`)

**业务描述**: SLO (服务水平目标) 定义表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `service_id` | Integer | FK | 否 | - | 关联服务ID |
| `name` | String(100) | - | 否 | - | SLO 名称 |
| `indicator_type` | String(50) | - | 是 | - | 指标类型 (Availability/Latency/Throughput) |
| `target_value` | Numeric | - | 是 | - | 目标值 |
| `metric_unit` | String(20) | - | 是 | - | 度量单位 (%/ms) |
| `time_window` | String(20) | - | 是 | - | 统计窗口期 (28d/7d) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **service**: many-to-one -> `Service`

---

### SystemRegistry (`mdm_systems_registry`)

**业务描述**: 三方系统注册表，记录对接的所有外部系统 (GitLab, Jira, Sonar 等)。 作为数据源治理注册中心，定义了连接方式、同步策略及数据治理属性。 - 用于管理 Collector 采集目标 - 用于 Issue Tracking 集成配置 支持 SCD Type 2 以审计连接配置的变更记录。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `system_code` | String(50) | PK | 否 | - | 系统唯一标准代号 (如 gitlab-corp) |
| `system_name` | String(100) | - | 否 | - | 系统显示名称 |
| `system_type` | String(50) | - | 是 | - | 工具类型 (VCS/TICKET/CI/SONAR/K8S) |
| `env_tag` | String(20) | - | 是 | PROD | 环境标签 (PROD/Stage/Test) |
| `base_url` | String(255) | - | 是 | - | API 基础地址 (Base URL) |
| `api_version` | String(20) | - | 是 | - | API 接口版本 (如 v4, api/v2) |
| `auth_type` | String(50) | - | 是 | - | 认证方式 (OAuth2/Token/Basic) |
| `credential_key` | String(100) | - | 是 | - | 凭证引用Key (指向Vault或Env Var) |
| `plugin_config` | JSON | - | 是 | - | 插件特定配置 (JSON, 如过滤规则、超时设置) |
| `sync_method` | String(50) | - | 是 | - | 同步方式 (CDC/Polling/Webhook) |
| `update_cycle` | String(50) | - | 是 | - | 更新频率 (Realtime/Hourly/Daily) |
| `enabled_plugins` | String(255) | - | 是 | - | 启用的采集插件列表 (逗号分隔) |
| `data_sensitivity` | String(20) | - | 是 | - | 数据敏感级 (L1-L4) |
| `sla_level` | String(20) | - | 是 | - | 服务等级 (P0-Critical / P1-High) |
| `technical_owner_id` | UUID | FK | 是 | - | 技术负责人ID |
| `is_active` | Boolean | - | 是 | True | 是否启用采集 |
| `last_heartbeat` | DateTime | - | 是 | - | 最后连通性检查时间 |
| `last_sync_at` | DateTime | - | 是 | - | 最后一次数据同步时间 |
| `remarks` | Text | - | 是 | - | 备注说明 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | (auto) | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **technical_owner**: many-to-one -> `User`
- **projects**: one-to-many -> `ProjectMaster`

---

### TraceabilityLink (`mdm_traceability_links`)

**业务描述**: 跨系统追溯链路表，连接需求与代码、测试与发布。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `source_system` | String(50) | - | 是 | - | 源系统 (jira/gitlab) |
| `source_type` | String(50) | - | 是 | - | 源实体类型 (requirement/story) |
| `source_id` | String(100) | INDEX | 是 | - | 源实体ID |
| `target_system` | String(50) | - | 是 | - | 目标系统 (gitlab/jenkins) |
| `target_type` | String(50) | - | 是 | - | 目标实体类型 (commit/merge_request/build) |
| `target_id` | String(100) | INDEX | 是 | - | 目标实体ID |
| `link_type` | String(50) | - | 是 | - | 链路类型 (implements/tests/deploys) |
| `raw_data` | JSON | - | 是 | - | 原始关联数据 (JSON) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### Vendor (`mdm_vendor`)

**业务描述**: 外部供应商主数据表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `vendor_code` | String(50) | PK | 否 | - | 供应商唯一编码 |
| `name` | String(200) | - | 否 | - | 供应商全称 |
| `short_name` | String(100) | - | 是 | - | 供应商简称 |
| `category` | String(50) | - | 是 | - | 供应商类别 (人力外包/软件许可/云服务/硬件) |
| `status` | String(20) | - | 是 | ACTIVE | 合作状态 (ACTIVE/BLACKLIST/INACTIVE) |
| `tax_id` | String(50) | - | 是 | - | 统一社会信用代码/税号 |
| `payment_terms` | String(100) | - | 是 | - | 默认账期 (e.g. Net 30, Net 60) |
| `currency` | String(10) | - | 是 | CNY | 默认结算币种 |
| `contact_person` | String(100) | - | 是 | - | 主要联系人 |
| `contact_email` | String(100) | - | 是 | - | 联系邮箱 |
| `contact_phone` | String(50) | - | 是 | - | 联系电话 |
| `rating` | Numeric | - | 是 | 0.0 | 供应商绩效评分 (0-5) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### ResourceCost (`stg_mdm_resource_costs`)

**业务描述**: 资源成本记录明细表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `service_id` | Integer | FK | 是 | - | 关联服务ID |
| `cost_code_id` | Integer | FK | 是 | - | 成本科目ID |
| `purchase_contract_id` | Integer | FK | 是 | - | 采购合同ID |
| `period` | String(20) | INDEX | 是 | - | 费用周期 (YYYY-MM) |
| `amount` | Numeric | - | 是 | 0.0 | 费用金额 |
| `currency` | String(10) | - | 是 | CNY | 币种 |
| `cost_type` | String(50) | - | 是 | - | 成本类型 (云资源/人力/软件) |
| `cost_item` | String(200) | - | 是 | - | 成本项目名称 |
| `vendor_name` | String(200) | - | 是 | - | 供应商名称 |
| `capex_opex_flag` | String(10) | - | 是 | - | CAPEX/OPEX标志 |
| `source_system` | String(100) | - | 是 | - | 数据来源系统 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **service**: many-to-one -> `Service`
- **cost_code**: many-to-one -> `CostCode`
- **purchase_contract**: many-to-one -> `PurchaseContract`

---

## 测试管理域

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
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **author**: many-to-one -> `User`
- **project**: many-to-one -> `GitLabProject`
- **test_cases**: one-to-many -> `GTMTestCase`

---

### GTMTestCaseIssueLink (`gtm_test_case_issue_links`)

**业务描述**: 测试用例与 Issue 的关联表 (gtm_test_case_issue_links)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | - |
| `test_case_id` | Integer | FK | 否 | - | - |
| `issue_id` | Integer | FK | 否 | - | - |
| `created_at` | DateTime | - | 是 | (auto) | - |
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
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **author**: many-to-one -> `User`
- **project**: many-to-one -> `GitLabProject`
- **linked_issues**: one-to-many -> `GitLabIssue`
- **associated_requirements**: one-to-many -> `GTMRequirement`
- **execution_records**: one-to-many -> `GTMTestExecutionRecord`

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
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **project**: many-to-one -> `GitLabProject`

---

### JenkinsTestExecution (`jenkins_test_executions`)

**业务描述**: Jenkins 测试执行汇总记录表。 存储来自 Jenkins 持续集成工具的测试报告汇总数据。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `project_id` | Integer | INDEX | 是 | - | 关联 GitLab 项目 ID |
| `build_id` | String(100) | INDEX | 否 | - | 构建 ID (Jenkins Build Number) |
| `test_level` | String(50) | - | 是 | - | 测试层级 (Unit/API/UI/Performance/Automation) |
| `test_tool` | String(100) | - | 是 | - | 测试工具 (Jenkins/JUnit/Pytest) |
| `total_cases` | Integer | - | 是 | 0 | 用例总数 |
| `passed_count` | Integer | - | 是 | 0 | 通过用例数 |
| `failed_count` | Integer | - | 是 | 0 | 失败用例数 |
| `skipped_count` | Integer | - | 是 | 0 | 跳过用例数 |
| `pass_rate` | Numeric | - | 是 | 0.0 | 通过率 (%) |
| `duration_ms` | Integer | - | 是 | 0 | 执行时长 (毫秒) |
| `raw_data` | JSON | - | 是 | - | 原始测试报告 JSON |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

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

- **project**: many-to-one -> `GitLabProject`

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

- **project**: many-to-one -> `GitLabProject`
- **author**: many-to-one -> `User`

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

- **project**: many-to-one -> `GitLabProject`

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

- **group**: many-to-one -> `GitLabGroup`
- **user**: many-to-one -> `User`

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

- **children**: one-to-many -> `GitLabGroup`
- **projects**: one-to-many -> `GitLabProject`
- **members**: one-to-many -> `GitLabGroupMember`
- **parent**: many-to-one -> `GitLabGroup`

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

- **author**: many-to-one -> `User`
- **project**: many-to-one -> `GitLabProject`
- **events**: one-to-many -> `GitLabIssueEvent`
- **transitions**: one-to-many -> `GitLabIssueStateTransition`
- **blockages**: one-to-many -> `GitLabBlockage`
- **milestone**: many-to-one -> `GitLabMilestone`
- **merge_requests**: one-to-many -> `GitLabMergeRequest`
- **associated_test_cases**: one-to-many -> `GTMTestCase`

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

- **deployments**: one-to-many -> `GitLabDeployment`
- **author**: many-to-one -> `User`
- **project**: many-to-one -> `GitLabProject`

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

- **project**: many-to-one -> `GitLabProject`
- **releases**: one-to-many -> `GitLabRelease`
- **issues**: one-to-many -> `GitLabIssue`

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

- **project**: many-to-one -> `GitLabProject`

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

- **project**: many-to-one -> `GitLabProject`
- **files**: one-to-many -> `GitLabPackageFile`

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

- **project**: many-to-one -> `GitLabProject`

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

- **role**: many-to-one -> `SysRole`
- **project**: many-to-one -> `GitLabProject`
- **user**: many-to-one -> `User`

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

- **group**: many-to-one -> `GitLabGroup`
- **organization**: many-to-one -> `Organization`
- **mdm_project**: many-to-one -> `ProjectMaster`
- **dependency_scans**: one-to-many -> `DependencyScan`
- **dependencies**: one-to-many -> `Dependency`
- **milestones**: one-to-many -> `GitLabMilestone`
- **members**: one-to-many -> `GitLabProjectMember`
- **commits**: one-to-many -> `GitLabCommit`
- **merge_requests**: one-to-many -> `GitLabMergeRequest`
- **issues**: one-to-many -> `GitLabIssue`
- **pipelines**: one-to-many -> `GitLabPipeline`
- **deployments**: one-to-many -> `GitLabDeployment`
- **test_cases**: one-to-many -> `GTMTestCase`
- **requirements**: one-to-many -> `GTMRequirement`
- **test_execution_records**: one-to-many -> `GTMTestExecutionRecord`
- **sonar_projects**: one-to-many -> `SonarProject`
- **jira_projects**: one-to-many -> `JiraProject`

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

- **project**: many-to-one -> `GitLabProject`
- **milestones**: one-to-many -> `GitLabMilestone`

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

- **project**: many-to-one -> `GitLabProject`

---

## 认证与授权域

### UserCredential (`sys_user_credentials`)

**业务描述**: 用户凭证表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `user_id` | UUID | FK, UNIQUE | 是 | - | 用户ID |
| `password_hash` | String(255) | - | 否 | - | 密码哈希值 |
| `last_login_at` | DateTime | - | 是 | - | 最后登录时间 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **user**: many-to-one -> `User`

---

### UserOAuthToken (`sys_user_oauth_tokens`)

**业务描述**: 用户 OAuth 令牌存储表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `user_id` | String(100) | INDEX | 是 | - | 用户标识 |
| `provider` | String(50) | INDEX | 是 | - | OAuth 提供商 (gitlab/github/azure) |
| `access_token` | String(1024) | - | 否 | - | 访问令牌 (加密存储) |
| `refresh_token` | String(1024) | - | 是 | - | 刷新令牌 |
| `token_type` | String(50) | - | 是 | - | 令牌类型 (Bearer) |
| `expires_at` | DateTime | - | 是 | - | 过期时间 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### UserRole (`sys_user_roles`)

**业务描述**: 用户与角色关联表 (sys_user_role)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `user_id` | UUID | PK, FK | 否 | - | 用户ID |
| `role_id` | Integer | PK, FK | 否 | - | 角色ID |

---

## 其他辅助域

### CommitMetrics (`commit_metrics`)

**业务描述**: 单个提交的详细度量数据 (ELOC)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `commit_id` | String(100) | PK | 否 | - | 提交SHA哈希值 |
| `project_id` | String(100) | FK | 是 | - | 所属业务项目ID |
| `author_email` | String(255) | INDEX | 是 | - | 提交者邮箱 |
| `committed_at` | DateTime | - | 是 | - | 提交时间 |
| `raw_additions` | Integer | - | 是 | 0 | 原始新增行数 |
| `raw_deletions` | Integer | - | 是 | 0 | 原始删除行数 |
| `eloc_score` | Numeric | - | 是 | 0.0 | 有效代码行数得分 |
| `impact_score` | Numeric | - | 是 | 0.0 | 代码影响力得分 |
| `churn_lines` | Integer | - | 是 | 0 | 代码翻动行数 |
| `comment_lines` | Integer | - | 是 | 0 | 注释行数 |
| `test_lines` | Integer | - | 是 | 0 | 测试代码行数 |
| `file_count` | Integer | - | 是 | 0 | 涉及文件数 |
| `is_merge` | Boolean | - | 是 | False | 是否为合并提交 |
| `is_legacy_refactor` | Boolean | - | 是 | False | 是否为遗留代码重构 |
| `refactor_ratio` | Numeric | - | 是 | 0.0 | 重构代码占比 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### DailyDevStats (`daily_dev_stats`)

**业务描述**: 开发人员行为的每日快照。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `user_id` | UUID | FK, INDEX | 是 | - | 用户ID |
| `date` | Date | INDEX | 是 | - | 统计日期 |
| `first_commit_time` | DateTime | - | 是 | - | 当日首次提交时间 |
| `last_commit_time` | DateTime | - | 是 | - | 当日最后提交时间 |
| `commit_count` | Integer | - | 是 | 0 | 当日提交次数 |
| `total_impact` | Numeric | - | 是 | 0.0 | 当日总影响力得分 |
| `total_churn` | Integer | - | 是 | 0 | 当日总代码翻动行数 |
| `created_at` | DateTime | - | 是 | (auto) | - |
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

- **scan**: many-to-one -> `DependencyScan`
- **project**: many-to-one -> `GitLabProject`
- **cves**: one-to-many -> `DependencyCVE`

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

- **dependency**: many-to-one -> `Dependency`

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

- **project**: many-to-one -> `GitLabProject`
- **dependencies**: one-to-many -> `Dependency`

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

- **project**: many-to-one -> `JiraProject`
- **sprints**: one-to-many -> `JiraSprint`

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

- **project**: many-to-one -> `JiraProject`
- **history**: one-to-many -> `JiraIssueHistory`
- **sprint**: many-to-one -> `JiraSprint`

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
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `raw_data` | JSON | - | 是 | - | - |

#### 关系映射

- **gitlab_project**: many-to-one -> `GitLabProject`
- **boards**: one-to-many -> `JiraBoard`
- **issues**: one-to-many -> `JiraIssue`

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

- **board**: many-to-one -> `JiraBoard`
- **issues**: one-to-many -> `JiraIssue`

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

- **project**: many-to-one -> `SonarProject`

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
| `created_at` | DateTime | - | 是 | (auto) | - |

#### 关系映射

- **project**: many-to-one -> `SonarProject`

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
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **gitlab_project**: many-to-one -> `GitLabProject`
- **measures**: one-to-many -> `SonarMeasure`
- **issues**: one-to-many -> `SonarIssue`
- **latest_measure**: many-to-one -> `SonarMeasure`

---

### RawDataStaging (`stg_raw_data`)

**业务描述**: 原始数据暂存表 (Staging 层)，用于存放未经处理的 API Payload。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `source` | String(50) | - | 是 | - | 数据来源系统 (gitlab/jira/sonar) |
| `entity_type` | String(50) | - | 是 | - | 实体类型 (project/issue/pipeline) |
| `external_id` | String(100) | INDEX | 是 | - | 外部系统记录ID |
| `payload` | JSON | - | 是 | - | 原始 JSON 数据负载 |
| `schema_version` | String(20) | - | 是 | - | Payload 结构版本 |
| `collected_at` | DateTime | - | 是 | - | 采集时间 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### SysMenu (`sys_menu`)

**业务描述**: 系统菜单/权限表 (sys_menu)。 统一管理系统菜单结构和功能权限标识。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 菜单ID |
| `menu_name` | String(50) | - | 否 | - | 菜单名称 |
| `parent_id` | Integer | FK | 是 | - | 父菜单ID (0或NULL表示顶级) |
| `order_num` | Integer | - | 是 | 0 | 显示顺序 |
| `path` | String(200) | - | 是 |  | 路由地址 |
| `component` | String(255) | - | 是 | - | 组件路径 |
| `query` | String(255) | - | 是 | - | 路由参数 |
| `is_frame` | Boolean | - | 是 | False | 是否为外链 |
| `is_cache` | Boolean | - | 是 | True | 是否缓存 |
| `menu_type` | String(1) | - | 是 |  | 菜单类型 (M目录 C菜单 F按钮) |
| `visible` | Boolean | - | 是 | True | 菜单状态 (True显示 False隐藏) |
| `status` | Boolean | - | 是 | True | 菜单状态 (True正常 False停用) |
| `perms` | String(100) | - | 是 | - | 权限标识 (e.g. system:user:list) |
| `icon` | String(100) | - | 是 | # | 菜单图标 |
| `remark` | String(500) | - | 是 |  | 备注 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **children**: one-to-many -> `SysMenu`
- **parent**: many-to-one -> `SysMenu`
- **roles**: one-to-many -> `SysRole`

---

### SysRole (`sys_role`)

**业务描述**: 系统角色表 (sys_role)。 扩展支持数据范围权限及角色继承。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 角色ID |
| `role_name` | String(30) | - | 否 | - | 角色名称 |
| `role_key` | String(100) | UNIQUE | 否 | - | 角色权限字符串 |
| `role_sort` | Integer | - | 否 | 0 | 显示顺序 |
| `data_scope` | Integer | - | 是 | 1 | 数据范围 |
| `parent_id` | Integer | - | 是 | 0 | 父角色ID (RBAC1) |
| `status` | Boolean | - | 是 | True | 角色状态 |
| `del_flag` | Boolean | - | 是 | False | 删除标志 |
| `remark` | String(500) | - | 是 | - | 备注 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **menus**: one-to-many -> `SysMenu`
- **depts**: one-to-many -> `Organization`
- **users**: one-to-many -> `User`

---

### SysRoleDept (`sys_role_dept`)

**业务描述**: 角色和部门关联表 (sys_role_dept)，用于自定义数据权限。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `role_id` | Integer | PK, FK | 否 | - | - |
| `dept_id` | String(100) | PK, FK | 否 | - | - |

---

### SysRoleMenu (`sys_role_menu`)

**业务描述**: 角色和菜单关联表 (sys_role_menu)。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `role_id` | Integer | PK, FK | 否 | - | - |
| `menu_id` | Integer | PK, FK | 否 | - | - |

---

### SyncLog (`sys_sync_logs`)

**业务描述**: 插件数据同步日志记录表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `project_id` | String(100) | INDEX | 是 | - | 关联项目ID |
| `status` | String(50) | - | 是 | - | 同步状态 (SUCCESS/FAILED/RUNNING) |
| `message` | Text | - | 是 | - | 同步结果信息 |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

---

### TeamMember (`sys_team_members`)

**业务描述**: 团队成员关联表。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `team_id` | Integer | FK | 否 | - | 团队ID |
| `user_id` | UUID | FK | 否 | - | 成员用户ID |
| `role_code` | String(50) | - | 是 | MEMBER | 团队角色 (LEADER/MEMBER/CONSULTANT) |
| `allocation_ratio` | Numeric | - | 是 | 1.0 | 工作量分配比例 (0.0-1.0) |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |

#### 关系映射

- **team**: many-to-one -> `Team`
- **user**: many-to-one -> `User`

---

### Team (`sys_teams`)

**业务描述**: 虚拟业务团队/项目组表。 支持 SCD Type 2，用于精确追踪团队名称、负责人及组织归属的历史变更， 确保 DORA 等效能指标能准确归因到"当时的团队"。

#### 字段定义

| 字段名 | 数据类型 | 约束 | 可空 | 默认值 | 说明 |
|:-------|:---------|:-----|:-----|:-------|:-----|
| `id` | Integer | PK | 否 | - | 自增主键 |
| `name` | String(100) | - | 否 | - | 团队名称 |
| `team_code` | String(50) | UNIQUE, INDEX | 是 | - | 团队代码 |
| `description` | Text | - | 是 | - | 团队描述 |
| `parent_id` | Integer | FK | 是 | - | 上级团队ID |
| `org_id` | String(100) | FK | 是 | - | 所属组织ID |
| `leader_id` | UUID | FK | 是 | - | 团队负责人ID |
| `created_at` | DateTime | - | 是 | (auto) | - |
| `updated_at` | DateTime | - | 是 | - | - |
| `sync_version` | Integer | - | 否 | 1 | - |
| `effective_from` | DateTime | - | 是 | (auto) | - |
| `effective_to` | DateTime | - | 是 | - | - |
| `is_current` | Boolean | INDEX | 是 | True | - |
| `is_deleted` | Boolean | - | 是 | False | - |

#### 关系映射

- **parent**: many-to-one -> `Team`
- **leader**: many-to-one -> `User`
- **members**: one-to-many -> `TeamMember`
- **children**: one-to-many -> `Team`

---


## 变更日志

### v2.2 (自动生成)
- 基于最新 SQLAlchemy 模型自动生成
- 支持变更检测和 Diff 对比
- 增强字段注释提取
- 优化默认值显示

---

**维护说明**: 本文档由 `scripts/generate_data_dictionary.py` 自动生成。
如需更新，请修改模型定义并运行 `make docs` 命令。

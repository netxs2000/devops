# 企业级 DevOps 数据字典 (Enterprise DevOps Data Dictionary)

**版本**: 2.2.0 (Analytics Extension)  
**日期**: 2025-12-16  
**状态**: 已生效 (Active)  
**维护人**: DevOps 效能平台团队

---

## 📖 1. 综述 (Overview)

本文档是 DevOps 数据采集器统一数据模型的唯一事实来源。系统基于 PostgreSQL 构建，采用星型模式设计，通过声明式 SQLAlchemy 模型实现数据的持久化管理。

### 核心架构设计

*   **统一基座 (Unified Base)**: 所有模型继承自统一的 `Base` 类，确保元数据（创建时间、更新时间）的一致性。
*   **统一身份认证 (Centralized Identity)**: 通过 `users` 表实现跨工具（GitLab, SonarQube）的身份归一化，支持离职员工和外部贡献者的虚拟身份管理。
*   **企业级多租户 (Enterprise Multi-tenancy)**: 依托 `organizations` 表实现 "公司 > 中心 > 部门 > 小组" 四级组织架构管理。

### 全局 ER 关系图

```mermaid
erDiagram
    %% Core Entities
    Organization ||--|{ Organization : "parent/child (父子组织)"
    Organization ||--|{ User : "contains (包含成员)"
    Organization ||--|{ Project : "owns (拥有资产)"

    %% User Relationships
    User ||--|{ Commit : "authors (提交代码)"
    User ||--|{ MergeRequest : "reviews/authors (提交MR)"
    User ||--|{ Issue : "reports (提单)"
    
    %% Project Scopes
    Project ||--|{ Commit : "contains (包含)"
    Project ||--|{ MergeRequest : "tracks (追踪)"
    Project ||--|{ Issue : "manages (管理)"
    Project ||--|{ Pipeline : "executes (执行)"
    Project ||--|{ Deployment : "deploys (部署)"
    Project ||--o{ Tag : "releases (发布)"
    Project ||--o{ Branch : "has (拥有分支)"
    Project ||--o{ Note : "discussions (讨论)"
    
    %% Detail Stats
    Commit ||--|{ CommitFileStats : "details (文件变更明细)"

    %% SonarQube Integration
    Project ||--o| SonarProject : "integrates (集成)"
    SonarProject ||--|{ SonarMeasure : "analyzes (质量快照)"
    SonarProject ||--|{ SonarIssue : "detects (发现问题)"
```

---

## 🏗️ 2. 公共基础模型 (Common Models)

跨插件共享的核心基础设施表。

### 2.1 组织架构 (`organizations`)
描述企业的层级结构，用于部门效能透视。

| 字段名        | 类型          | 键   | 必填  | 默认值 | 示例数据          | 业务说明                                                                 |
|:--------------|:--------------|:----:|:-----:|:-------|:------------------|:-------------------------------------------------------------------------|
| `id`          | Integer       | PK   | 是    | Auto   | `1001`            | 内部组织 ID (自增)                                                       |
| `name`        | String(200)   |      | 是    | -      | `"研发中心"`      | 组织单元名称                                                             |
| `level`       | String(20)    |      | 否    | -      | `"Center"`        | 层级类型: `Company`(公司), `Center`(中心), `Department`(部门), `Group`(组) |
| `parent_id`   | Integer       | FK   | 否    | NULL   | `1`               | 父级组织 ID (自关联 `organizations.id`)                                  |
| `created_at`  | DateTime      |      | 否    | Now    | `2024-01-01`      | 创建时间                                                                 |
| `updated_at`  | DateTime      |      | 否    | Now    | `2024-01-02`      | 更新时间                                                                 |

### 2.2 全局用户 (`users`)
统一的自然人身份表，解决跨系统账号不一致问题。

| 字段名            | 类型          | 键   | 必填  | 默认值 | 示例数据                  | 业务说明                                                 |
|:------------------|:--------------|:----:|:-----:|:-------|:--------------------------|:---------------------------------------------------------|
| `id`              | Integer       | PK   | 是    | Auto   | `10086`                   | 全局用户 ID                                              |
| `gitlab_id`       | Integer       | UK   | 否    | NULL   | `888`                     | 原始 GitLab ID (关联 `users.id`)，虚拟用户此列为 NULL    |
| `username`        | String(100)   |      | 否    | -      | `"zhangsan"`              | 登录使用的用户名                                         |
| `name`            | String(200)   |      | 否    | -      | `"张三"`                  | 显示名称 (中文名)                                        |
| `email`           | String(200)   |      | 否    | -      | `"zhangsan@corp.com"`     | 企业邮箱                                                 |
| `state`           | String(20)    |      | 否    | -      | `"active"`                | 账号状态: `active`(激活), `blocked`(禁用)                |
| `is_virtual`      | Boolean       |      | 否    | False  | `False`                   | **是否虚拟账号** (True=手工维护, False=自动同步)         |
| `department`      | String(100)   |      | 否    | -      | `"基础架构部"`            | 部门快照字符串 (源自 Profile)                            |
| `organization_id` | Integer       | FK   | 否    | NULL   | `1001`                    | 归属组织架构 ID (关联 `organizations.id`)                |
| `avatar_url`      | String(500)   |      | 否    | -      | `"http://..."`            | 头像地址                                                 |
| `raw_data`        | JSON          |      | 否    | -      | `{"id": 888, ...}`        | 原始数据备份                                             |

### 2.3 同步日志 (`sync_logs`)
数据采集任务的审计追踪。

| 字段名             | 类型         | 键   | 必填  | 默认值   | 示例数据             | 业务说明                         |
|:-------------------|:-------------|:----:|:-----:|:---------|:---------------------|:---------------------------------|
| `id`               | Integer      | PK   | 是    | Auto     | `500`                | 日志 ID                          |
| `source`           | String(20)   |      | 否    | 'gitlab' | `"gitlab"`           | 数据源: `gitlab`, `sonarqube`    |
| `project_id`       | Integer      |      | 否    | -        | `12345`              | 关联的项目内部 ID                |
| `project_key`      | String(200)  |      | 否    | -        | `"com.corp:demo"`    | 项目标识 Key (Sonar 用)          |
| `status`           | String(20)   |      | 否    | -        | `"SUCCESS"`          | 任务状态: `SUCCESS`, `FAILED`    |
| `duration_seconds` | Integer      |      | 否    | -        | `45`                 | 耗时 (秒)                        |
| `records_synced`   | Integer      |      | 否    | -        | `120`                | 同步条数                         |
| `timestamp`        | DateTime     |      | 否    | Now      | `2025-12-14 10:00`   | 执行时间                         |

---

## 🦊 3. GitLab 数据域 (GitLab Domain)

覆盖研发全生命周期：计划 -> 编码 -> 构建 -> 部署。

### 3.1 群组 (`gitlab_groups`) (New)
GitLab 的组织单元，用于管理项目和子群组。

| 字段名        | 类型          | 键   | 必填  | 默认值 | 示例数据                  | 业务说明                                   |
|:--------------|:--------------|:----:|:-----:|:-------|:--------------------------|:-------------------------------------------|
| `id`          | Integer       | PK   | 是    | -      | `99`                      | **GitLab Group ID**                        |
| `name`        | String(255)   |      | 是    | -      | `"Backend Team"`          | 群组名称                                   |
| `path`        | String(255)   |      | 是    | -      | `"backend"`               | URL 路径片段                               |
| `full_path`   | String(500)   | UK   | 是    | -      | `"tech/backend"`          | 完整路径                                   |
| `description` | Text          |      | 否    | -      | `"后端研发部"`            | 描述信息                                   |
| `parent_id`   | Integer       | FK   | 否    | NULL   | `88`                      | 父群组 ID (自关联 `gitlab_groups.id`)      |
| `visibility`  | String(20)    |      | 否    | -      | `"private"`               | 可见性: `public`, `private`, `internal`    |
| `avatar_url`  | String(500)   |      | 否    | -      | `"http://..."`            | 图标                                       |
| `web_url`     | String(500)   |      | 否    | -      | `"http://gitlab.../tech"` | Web 地址                                   |
| `created_at`  | DateTime      |      | 否    | -      | `2024-01-01`              | 创建时间                                   |
| `updated_at`  | DateTime      |      | 否    | -      | `2024-01-02`              | 更新时间                                   |

### 3.2 群组成员 (`gitlab_group_members`) (New)
记录用户与群组的关联权限，用于安全审计和人力管理。

| 字段名         | 类型         | 键      | 必填  | 默认值 | 示例数据      | 业务说明                                      |
|:---------------|:-------------|:-------:|:-----:|:-------|:--------------|:----------------------------------------------|
| `id`           | Integer      | PK      | 是    | Auto   | `555`         | 记录 ID                                       |
| `group_id`     | Integer      | FK      | 是    | -      | `99`          | 关联群组 ID (关联 `gitlab_groups.id`)         |
| `user_id`      | Integer      | FK      | 是    | -      | `10086`       | 关联系统用户 ID (关联 `users.id`)             |
| `gitlab_uid`   | Integer      |         | 是    | -      | `888`         | 原始 GitLab User ID (用于匹配)                |
| `access_level` | Integer      |         | 是    | -      | `30`          | 权限值: 10(Guest), 30(Dev), 40(Maintainer), 50(Owner) |
| `state`        | String(20)   |         | 否    | -      | `"active"`    | 状态: `active`, `awaiting`, `invited`         |
| `joined_at`    | DateTime     |         | 否    | -      | `2024-01-01`  | 加入时间                                      |
| `expires_at`   | DateTime     |         | 否    | NULL   | `2024-12-31`  | 权限过期时间 (外包/临时权限常用)              |

### 3.3 项目 (`projects`)
研发资产的核心容器。

| 字段名                | 类型         | 键   | 必填  | 默认值     | 示例数据                    | 业务说明                                         |
|:----------------------|:-------------|:----:|:-----:|:-----------|:----------------------------|:-------------------------------------------------|
| `id`                  | Integer      | PK   | 是    | -          | `1010`                      | **GitLab 原始 Project ID** (保留原值以简化关联)  |
| `name`                | String       |      | 否    | -          | `"DevOps Platform"`         | 项目名称                                         |
| `path_with_namespace` | String       |      | 否    | -          | `"infra/devops-platform"`   | 完整路径 (如 `group/subgroup/project`)           |
| `department`          | String       |      | 否    | -          | `"效能工具组"`              | 部门 (从顶层 Group 描述字段解析)                 |
| `group_id`            | Integer      | FK   | 否    | NULL       | `99`                        | **归属群组 ID** (关联 `gitlab_groups.id`)        |
| `organization_id`     | Integer      | FK   | 否    | NULL       | `1001`                      | 归属组织 (关联 `organizations.id`)               |
| `sync_status`         | String       |      | 否    | 'PENDING'  | `"COMPLETED"`               | 同步状态机: `PENDING`, `SYNCING`, `COMPLETED`    |
| `storage_size`        | BigInteger   |      | 否    | -          | `104857600`                 | 仓库物理大小 (Bytes)                             |
| `star_count`          | Integer      |      | 否    | -          | `56`                        | 关注数                                           |
| `forks_count`         | Integer      |      | 否    | -          | `12`                        | 复刻数                                           |
| `visibility`          | String       |      | 否    | -          | `"private"`                 | 可见性 (public/internal/private)                 |
| `archived`            | Boolean      |      | 否    | False      | `True`                      | 是否归档 (True=已归档)                           |

### 3.2 提交 (`commits`)
代码变更的历史记录。

| 字段名           | 类型      | 键      | 必填  | 默认值 | 示例数据                  | 业务说明                           |
|:-----------------|:----------|:-------:|:-----:|:-------|:--------------------------|:-----------------------------------|
| `id`             | String    | PK      | 是    | -      | `"a1b2c3d4..."`           | Commit SHA 哈希值                  |
| `project_id`     | Integer   | PK, FK  | 是    | -      | `1010`                    | 归属项目 ID (复合主键)             |
| `short_id`       | String    |         | 否    | -      | `"a1b2c3d4"`              | 短 SHA (前8位)                     |
| `title`          | String    |         | 否    | -      | `"feat: add new api"`     | 提交标题                           |
| `author_name`    | String    |         | 否    | -      | `"Zhang San"`             | Git 提交人姓名                     |
| `author_email`   | String    |         | 否    | -      | `"zhangsan@corp.com"`     | Git 提交人邮箱                     |
| `committed_date` | DateTime  |         | 否    | -      | `2024-01-15 14:30`        | 提交时间                           |
| `additions`      | Integer   |         | 否    | -      | `150`                     | 增加行数                           |
| `deletions`      | Integer   |         | 否    | -      | `20`                      | 删除行数                           |
| `total`          | Integer   |         | 否    | -      | `170`                     | 变更总行数                         |
| `gitlab_user_id` | Integer   | FK      | 否    | NULL   | `10086`                   | 关联内部用户 ID (关联 `users.id`)  |

### 3.3 提交文件统计 (`commit_file_stats`) 🌟
每次提交中每个文件的变更明细，用于精准识别有效代码产出。

| 字段名          | 类型      | 键   | 必填  | 默认值 | 示例数据               | 业务说明           |
|:----------------|:----------|:----:|:-----:|:-------|:-----------------------|:-------------------|
| `id`            | Integer   | PK   | 是    | Auto   | `50001`                | 自增 ID            |
| `commit_id`     | String    | FK   | 否    | -      | `"a1b2c3d4..."`        | 关联 Commit SHA    |
| `file_path`     | String    |      | 否    | -      | `"src/main.py"`        | 变更文件路径       |
| `language`      | String    |      | 否    | -      | `"Python"`             | 编程语言类型       |
| `code_added`    | Integer   |      | 否    | 0      | `50`                   | **代码**增加行数   |
| `comment_added` | Integer   |      | 否    | 0      | `10`                   | **注释**增加行数   |
| `blank_added`   | Integer   |      | 否    | 0      | `5`                    | **空行**增加行数   |

### 3.4 合并请求 (`merge_requests`)
代码评审 (Code Review) 过程记录。

| 字段名          | 类型      | 键   | 必填  | 默认值 | 示例数据                   | 业务说明                         |
|:----------------|:----------|:----:|:-----:|:-------|:---------------------------|:---------------------------------|
| `id`            | Integer   | PK   | 是    | -      | `2050`                     | GitLab MR 全局 ID                |
| `iid`           | Integer   |      | 否    | -      | `15`                       | 项目内 MR 编号 (如 !15)          |
| `project_id`    | Integer   | FK   | 否    | -      | `1010`                     | 归属项目                         |
| `title`         | String    |      | 否    | -      | `"Refactor user model"`    | 标题                             |
| `state`         | String    |      | 否    | -      | `"merged"`                 | 状态: `opened`, `merged`, `closed`|
| `author_id`     | Integer   | FK   | 否    | -      | `10086`                    | 发起人 (关联 `users.id`)         |
| `created_at`    | DateTime  |      | 否    | -      | `2024-02-01 09:00`         | 创建时间                         |
| `merged_at`     | DateTime  |      | 否    | NULL   | `2024-02-02 18:00`         | 合并时间 (计算 Review 耗时)      |
| `changes_count` | String    |      | 否    | -      | `"10"`                     | 变更文件数                       |

### 3.5 议题 (`issues`)
需求与缺陷管理。

| 字段名             | 类型      | 键   | 必填  | 默认值 | 示例数据                  | 业务说明                         |
|:-------------------|:----------|:----:|:-----:|:-------|:--------------------------|:---------------------------------|
| `id`               | Integer   | PK   | 是    | -      | `3050`                    | Issue 全局 ID                    |
| `iid`              | Integer   |      | 否    | -      | `102`                     | 项目内编号 (如 #102)             |
| `project_id`       | Integer   | FK   | 否    | -      | `1010`                    | 归属项目                         |
| `title`            | String    |      | 否    | -      | `"Fix login bug"`         | 标题                             |
| `time_estimate`    | Integer   |      | 否    | NULL   | `3600`                    | 预估工时 (秒)                    |
| `total_time_spent` | Integer   |      | 否    | NULL   | `7200`                    | 实际耗时 (秒)                    |
| `author_id`        | Integer   | FK   | 否    | -      | `10086`                   | 提单人 (关联 `users.id`)         |
| `labels`           | JSON      |      | 否    | -      | `["bug", "P0"]`           | 标签集合                         |

### 3.6 讨论笔记 (`notes`)
MR 和 Issue 中的评论互动。

| 字段名          | 类型      | 键   | 必填  | 默认值 | 示例数据                  | 业务说明                                      |
|:----------------|:----------|:----:|:-----:|:-------|:--------------------------|:----------------------------------------------|
| `id`            | Integer   | PK   | 是    | -      | `8001`                    | Note ID                                       |
| `noteable_type` | String    |      | 否    | -      | `"MergeRequest"`          | 对象类型: `MergeRequest`, `Issue`             |
| `noteable_iid`  | Integer   |      | 否    | -      | `15`                      | 对象项目内编号                                |
| `body`          | String    |      | 否    | -      | `"Please fix lint error"` | 评论内容                                      |
| `system`        | Boolean   |      | 否    | False  | `False`                   | 是否系统消息 (True=系统生成, False=人工评论)  |
| `resolvable`    | Boolean   |      | 否    | False  | `True`                    | 是否需要在此处打钩解决 (用于 CR 统计)         |

### 3.7 流水线 (`pipelines`)
CI/CD 持续集成执行记录。

| 字段名       | 类型      | 键   | 必填  | 默认值 | 示例数据             | 业务说明                        |
|:-------------|:----------|:----:|:-----:|:-------|:---------------------|:--------------------------------|
| `id`         | Integer   | PK   | 是    | -      | `9001`               | Pipeline ID                     |
| `project_id` | Integer   | FK   | 否    | -      | `1010`               | 归属项目                        |
| `status`     | String    |      | 否    | -      | `"success"`          | 状态: `success`, `failed`, `canceled` |
| `duration`   | Integer   |      | 否    | -      | `300`                | 运行时长 (秒)                   |
| `coverage`   | String    |      | 否    | NULL   | `"85.4"`             | 单元测试覆盖率 (如 "85.4")      |
| `source`     | String    |      | 否    | -      | `"push"`             | 触发源 (如 `push`, `schedule`)  |

### 3.8 部署 (`deployments`)
DORA 指标核心数据源，记录发布行为。

| 字段名        | 类型      | 键   | 必填  | 默认值 | 示例数据             | 业务说明                     |
|:--------------|:----------|:----:|:-----:|:-------|:---------------------|:-----------------------------|
| `id`          | Integer   | PK   | 是    | -      | `4001`               | Deployment ID                |
| `project_id`  | Integer   | FK   | 否    | -      | `1010`               | 归属项目                     |
| `environment` | String    |      | 否    | -      | `"production"`       | 环境名称 (如 `production`)   |
| `status`      | String    |      | 否    | -      | `"success"`          | 部署结果                     |
| `created_at`  | DateTime  |      | 否    | -      | `2024-03-01 12:00`   | 部署时间                     |
| `ref`         | String    |      | 否    | -      | `"main"`             | 部署分支/Tag                 |

### 3.9 分支与标签 (`branches` / `tags`)
Git 引用信息。

| 模型       | 关键字段                                  | 说明                             |
|:-----------|:------------------------------------------|:---------------------------------|
| **Branch** | `name`, `last_commit_date`, `is_merged`   | 用于分析分支活跃度和清理僵尸分支 |
| **Tag**    | `name`, `message`, `commit_sha`           | 用于标记发布版本里程碑           |

### 3.10 里程碑 (`milestones`) (New)
项目迭代与版本规划。

| 字段名        | 类型      | 键   | 必填  | 默认值 | 示例数据             | 业务说明                     |
|:--------------|:----------|:----:|:-----:|:-------|:---------------------|:-----------------------------|
| `id`          | Integer   | PK   | 是    | -      | `6001`               | Milestone ID                 |
| `project_id`  | Integer   | FK   | 否    | -      | `1010`               | 归属项目                     |
| `title`       | String    |      | 否    | -      | `"v1.2.0 Sprint"`    | 里程碑标题                   |
| `state`       | String    |      | 否    | -      | `"active"`           | 状态: `active`, `closed`     |
| `due_date`    | DateTime  |      | 否    | -      | `2024-04-01`         | **截止日期 (死线)**          |
| `start_date`  | DateTime  |      | 否    | -      | `2024-03-01`         | 开始日期                     |

---

## 📡 4. SonarQube 数据域 (Quality Domain)

代码质量静态扫描数据。

### 4.1 质量项目 (`sonar_projects`)
SonarQube 项目映射。

| 字段名                | 类型          | 键   | 必填  | 默认值   | 示例数据                  | 业务说明                            |
|:----------------------|:--------------|:----:|:-----:|:---------|:--------------------------|:------------------------------------|
| `id`                  | Integer       | PK   | 是    | Auto     | `2001`                    | 内部 ID                             |
| `key`                 | String        | UK   | 是    | -        | `"com.corp:demo"`         | Sonar 项目 Key (如 `com.corp:app`)  |
| `name`                | String        |      | 否    | -        | `"Demo Project"`          | 项目显示名称                        |
| `gitlab_project_id`   | Integer       | FK   | 否    | NULL     | `1010`                    | 关联的 GitLab 项目 (自动推断)       |
| `last_analysis_date`  | DateTime      |      | 否    | -        | `2024-03-05 10:00`        | 最后一次扫描时间                    |

### 4.2 质量快照 (`sonar_measures`)
随时间变化的代码质量评分历史。

| 字段名                | 类型          | 键   | 必填  | 默认值 | 示例数据          | 业务说明                 |
|:----------------------|:--------------|:----:|:-----:|:-------|:------------------|:-------------------------|
| `id`                       | Integer       | PK   | 是    | Auto   | `7001`            | 记录 ID                                      |
| `project_id`               | Integer       | FK   | 是    | -      | `2001`            | 关联 Sonar 项目                              |
| `analysis_date`            | DateTime      |      | 是    | -      | `2024-03-05 10:00`| 快照生成时间                                 |
| `files`                    | Integer       |      | 否    | -      | `50`              | 文件数                                       |
| `lines`                    | Integer       |      | 否    | -      | `6000`            | 总行数                                       |
| `ncloc`                    | Integer       |      | 否    | -      | `5000`            | 有效代码行数                                 |
| `classes`                  | Integer       |      | 否    | -      | `20`              | 类数量                                       |
| `functions`                | Integer       |      | 否    | -      | `100`             | 方法数量                                     |
| `statements`               | Integer       |      | 否    | -      | `2000`            | 语句数量                                     |
| `bugs`                     | Integer       |      | 否    | -      | `5`               | **Bug 数量 (总计)**                          |
| `bugs_blocker`             | Integer       |      | 否    | 0      | `1`               | Bug - 阻塞级别                               |
| `bugs_critical`            | Integer       |      | 否    | 0      | `1`               | Bug - 严重级别                               |
| `bugs_major`               | Integer       |      | 否    | 0      | `2`               | Bug - 主要级别                               |
| `bugs_minor`               | Integer       |      | 否    | 0      | `1`               | Bug - 次要级别                               |
| `bugs_info`                | Integer       |      | 否    | 0      | `0`               | Bug - 提示级别                               |
| `vulnerabilities`          | Integer       |      | 否    | -      | `0`               | **漏洞数量 (总计)**                          |
| `vulnerabilities_blocker`  | Integer       |      | 否    | 0      | `0`               | 漏洞 - 阻塞级别                              |
| `vulnerabilities_critical` | Integer       |      | 否    | 0      | `0`               | 漏洞 - 严重级别                              |
| `vulnerabilities_major`    | Integer       |      | 否    | 0      | `0`               | 漏洞 - 主要级别                              |
| `vulnerabilities_minor`    | Integer       |      | 否    | 0      | `0`               | 漏洞 - 次要级别                              |
| `vulnerabilities_info`     | Integer       |      | 否    | 0      | `0`               | 漏洞 - 提示级别                              |
| `security_hotspots`        | Integer       |      | 否    | -      | `2`               | **安全热点 (总计)**                          |
| `security_hotspots_high`   | Integer       |      | 否    | 0      | `1`               | 安全热点 - 高风险                            |
| `security_hotspots_medium` | Integer       |      | 否    | 0      | `1`               | 安全热点 - 中风险                            |
| `security_hotspots_low`    | Integer       |      | 否    | 0      | `0`               | 安全热点 - 低风险                            |
| `complexity`               | Integer       |      | 否    | -      | `150`             | 圈复杂度                                     |
| `cognitive_complexity`     | Integer       |      | 否    | -      | `100`             | 认知复杂度                                   |
| `comment_lines_density`    | Float         |      | 否    | -      | `10.5`            | 注释行密度 (%)                               |
| `duplicated_lines_density` | Float         |      | 否    | -      | `2.1`             | 重复行密度 (%)                               |
| `coverage`                 | Float         |      | 否    | -      | `85.5`            | **覆盖率 (%)**                               |
| `sqale_index`              | Integer       |      | 否    | -      | `120`             | **技术债务** (分钟)                          |
| `sqale_debt_ratio`         | Float         |      | 否    | -      | `1.2`             | 技术债务率 (%)                               |
| `quality_gate_status`      | String        |      | 否    | -      | `"OK"`            | 质量门禁: `OK`, `ERROR`                      |

### 4.3 代码问题 (`sonar_issues`)
具体的代码违规详情（需要在配置中显式开启同步）。

| 字段名      | 类型      | 键   | 必填  | 默认值 | 示例数据                  | 业务说明                                     |
|:------------|:----------|:----:|:-----:|:-------|:--------------------------|:---------------------------------------------|
| `id`            | Integer   | PK   | 是    | Auto   | `8888`                    | 记录 ID                                      |
| `project_id`    | Integer   | FK   | 是    | -      | `2001`                    | 关联 Sonar 项目                              |
| `issue_key`     | String    | UK   | 是    | -      | `"AX3v4..."`              | 问题唯一标识                                 |
| `type`          | String    |      | 否    | -      | `"CODE_SMELL"`            | 类型: `BUG`, `VULNERABILITY`, `CODE_SMELL`   |
| `severity`      | String    |      | 否    | -      | `"MAJOR"`                 | 严重度: `BLOCKER`, `CRITICAL`...             |
| `status`        | String    |      | 否    | -      | `"OPEN"`                  | 状态: `OPEN`, `RESOLVED`...                  |
| `author`        | String    |      | 否    | -      | `"zhangsan"`              | **责任人** (Email 或 Username)               |
| `creation_date` | DateTime  |      | 否    | -      | `2024-03-01`              | 问题引入时间                                 |
| `component`     | String    |      | 否    | -      | `"src/utils.py"`          | 相关文件路径                                 |
| `line`          | Integer   |      | 否    | -      | `45`                      | 行号                                         |
| `effort`        | String    |      | 否    | -      | `"10min"`                 | 修复预估时间                                 |

---
*Generated by DevOps AntiGravity Agent*

## 📊 5. 分析视图 (Analytics Views)

基于基础表构建的高级数据模型 (Data Mart)�?

### 5.1 项目全景 (`view_project_overview`)
*   **用�?*: 项目维度的全量宽表�?
*   **关键字段**: `issue_completion_pct`, `time_variance_hours`, `quality_gate`, `active_rate_pct`.

### 5.2 PMO 战略看板 (`view_pmo_*`)
*   **资源热力�?*: `view_pmo_resource_heatmap` (字段: `resource_share_pct`, `project_tier`)
*   **部门效能�?*: `view_pmo_dept_ranking` (字段: `rank_speed`, `rank_stability`)
*   **战略矩阵**: `view_pmo_portfolio_matrix` (字段: `x_axis_velocity`, `y_axis_health`, `quadrant`)
*   **风险治理**: `view_pmo_governance_risk` (字段: `bypass_rate_pct`, `active_blockers`)
*   **创新指数**: `view_pmo_innovation_metrics` (字段: `cross_pollination_index`)
*   **客户满意�?*: `view_pmo_customer_satisfaction` (字段: `satisfaction_prediction`)
*   **ROI 效能**: `view_pmo_roi_efficiency` (字段: `throughput_per_fte`, `avg_hours_per_issue`)

### 5.3 HR 人才洞察 (`view_hr_*`)
*   **能力画像**: `view_hr_user_capability_profile`
*   **技术栈**: `view_hr_user_tech_stack`
*   **流失风险**: `view_hr_retention_risk` (字段: `burnout_risk_level`)
*   **质量计分�?*: `view_hr_user_quality_scorecard`

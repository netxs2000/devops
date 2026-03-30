# DevOps Platform Project Contexts (Development Constitution)

> **Document Positioning**: This file is the project-specific constitution for **DevOps Platform**.
> - **全局原则 (Global Rules)**: 基础 AI 协作哲学定义在 `~/.gemini/gemini.md`。
> - **AI 导航路由 (Meta-Prompt)**: 自动化代理的入场规则及核心文档衔接约束定义在库根目录 `AGENTS.md`。
> - **项目宪法 (Project Contexts)**: 本文件（`contexts.md`）包含具体的架构、代码规范及运维红线。
> 
> *优先级：`contexts.md` (业务最高源) > `AGENTS.md` (调度层) > `gemini.md` (全局)。发生冲突时按此优先级执行。*


## 1. 项目概览 (Overview)
**DevOps Data Application Platform** 是一套企业级研发效能数据底座。它通过插件化架构采集 GitLab, SonarQube, Jenkins, Zentao, Nexus 等工具链数据，并利用 dbt 进行指标建模，最终通过 Apple Style 的原生前端界面提供看板与追溯能力。


## 2. 核心技术栈 (Technology Stack)
- **后端 (Backend)**: Python 3.12, FastAPI (Router-Service 模式), SQLAlchemy 2.0 (Typed).
- **数据层 (Data)**: PostgreSQL 15, dbt (数据转换层), RabbitMQ (任务分发控制).
- **前端 (Frontend)**: Native JS/CSS (Apple Style Edition), Web Components, 全局变量约束通信.
- **运维 (DevOps)**: Docker Compose, 多阶段镜像构建, 离线 Tar 包部署支持.


## 3. 开发环境与兼容性 (Environment)
- **开发与测试环境 (Dev & Test Env)**: 
    - **主验证环境 (Primary)**: **Docker Desktop (Linux 模式)**。所有功能逻辑、数据库变更、集成测试**必须**首先在容器内验证。
    - **辅助/调试环境 (Auxiliary)**: Windows + PowerShell。仅用于代码编写、轻量级 Lint 检查及辅助脚本调试。
    - **核心原则**: 严禁以“Windows 能跑通”作为提测标准。物理真实环境以 Docker 内的 Linux 表现为准。通过 `make test` 或 `docker-compose exec api pytest` 确保 100% 环境对齐。
- **路径处理**: 强制使用 `pathlib` 确保跨平台路径兼容。
- **临时输出归集 [MANDATORY]**: 严禁在根目录直接生成临时过程文件或导出结果。所有临时调试脚本、手动导出 CSV、日志重定向（Redirect）必须明确指向 `./tmp/` 或 `./data/temp/` 目录。
- **CSV 编码**: 所有 CSV 文件的生成、读取及模版任务强制使用 `utf-8-sig` 编码，确保在 Windows Office/Excel 环境下打开不出现汉字乱码。
- **语义分层规范 (Semantic Alignment)**:
    - **技术侧用英文**: 数据库字段名、API Schema、核心代码变量必须使用标准英文命名（如 `pm_user_id`）。
    - **业务侧用中文**: 数据库 `comment`、CSV 导入/导出表头、UI 界面显示、报表评估指标必须使用专业业务中文术语（如：项目经理、负责人邮箱、交付周期、ELOC等）。
    - **高度自适应映射**: 脚本层应实现“业务 -> 技术”的自动解析（如通过邮箱自动匹配 ID，通过中文表头自动匹配字段），确保护业务维护的低成本。
- **配置一致性**: 所有敏感配置统一通过 `.env` 注入，严禁硬编码 API 地址。
    - **Pydantic 规范**: 使用双下划线 (`__`) 分隔嵌套配置（如 `GITLAB__URL` 映射到 `config.gitlab.url`）。
    - **脱敏**: Logger 必须屏蔽任何包含 `token`, `password`, `key` 的字段。


## 4. 核心架构与插件开发 (Architecture)
- **Plugin Factory**: 插件位于 `devops_collector/plugins/`，结构必须遵循以下标准：
    ```
    plugins/{plugin_name}/
        __init__.py      # 必须包含 register() 函数
        client.py        # API 客户端，继承 BaseClient
        worker.py        # 任务处理器，继承 BaseWorker
        models.py        # SQLAlchemy 模型定义
        schemas.py       # Pydantic 请求/响应模型 (可选)
    ```
- **Router-Service 模式**: 
    - **Router 层**: 仅负责路由定义、参数校验（Pydantic）、权限控制、依赖注入及调用 Service。严禁在 Router 中编写业务逻辑或直接操作多表数据库。必须定义 `response_model`，严禁直接返回 SQLAlchemy 对象。
    - **Service 层**: 承载核心业务逻辑、复杂计算、跨表事务。Service 函数应具备原子性，方便被多个 Router 或定时任务复用。多表操作强制使用 `with db.begin():` 包裹。
- **身份治理映射**: 全球唯一 `global_user_id` 连接各系统账号，置信度通过 `IdentityResolver` 算法动态计算。
- **Security Scans**: 采用 **CI-Driven** 模式。DevOps 平台不运行本地扫描器（如 Java/Dependency-Check），而是通过 API 接收 CI 流水线上传的 JSON 报告。这降低了平台容器的体积与资源消耗。

### 4.1 数据采集管道性能规范 (Data Pipeline Performance) [MANDATORY]

> **背景**: 2026-03-18 在优化数据加载器时发现，逐条 `save_to_staging` 在 23W+ 记录量级下成为主要性能瓶颈。
> 以下规范为从实战中提炼的强制性准则。

- **Staging 写入分级 (Tiered Staging Write)**:
    - **批量实体 (Commit, Issue, MR, Pipeline, Task, Bug)**: 必须调用 `bulk_save_to_staging()`。该方法使用 PostgreSQL 原生 `COPY FROM` + 临时表 Upsert，将 N 次数据库往返压缩为 2 次。
    - **单条低频实体 (Product, Project, Group)**: 允许使用 `save_to_staging()`（逐条 Upsert）。
    - **判断标准**: 若单次同步周期内该实体类型的记录数可能超过 **10 条**，必须走 `bulk_save_to_staging`。
- **Transform 层批处理 (Batch Transform)** [MANDATORY]:
    - **预加载模式**: 严禁在循环内逐条执行 `session.query(Model).filter_by(id=x).first()`（N+1 查询反模式）。必须在循环前通过 `session.query(Model).filter(Model.id.in_(batch_ids))` 一次性加载为 Map。
    - **延迟 Flush**: 严禁在循环内逐条 `session.flush()`。所有 ORM 对象变更必须在循环结束后统一执行一次 `session.flush()`。
    - **批次粒度**: 默认 batch_size = 500（`BaseMixin._process_generator`）。GitLab 类插件必须使用该框架。ZenTao 类插件若一次性获取全量数据，应在调用方先收集为 list 再传入批量方法。
- **事务安全 (Transaction Safety)**:
    - 批量方法执行后必须显式 `session.commit()`，失败时必须 `session.rollback()`，严禁吞噬异常。
    - 单条兼容接口（如 `_sync_issue`）必须内部委托给批量方法，传入 `[data]`，确保代码路径统一。


## 5. 数据库开发规范 (Database & SCD)

### 5.1 Surrogate PK 准则 (Surrogate PK Principle) [MANDATORY]
- **物理主键 (Physical PK)**: **所有**数据库表（除部分 N:N 关联表外）必须强制包含一个名为 `id` 的物理主键，严禁使用业务编码作为物理 PK。
- **主键类型 (PK Types)**:
    - `User` (mdm_identities): 使用 `UUID` (字段名为 `global_user_id` 并别名为 `id`)，以支持多源身份归一。
    - **其它表**: 统一使用 **BigInteger** 自增主键。
- **关联解耦 (Relationship Decoupling)**: 所有的 `ForeignKey` 必须指向父表的物理 `id`。严禁跨表透传业务编码（如 `project_id`, `org_id`）作为关联手段，防止业务重命名时触发级联故障。
- **业务标识 (Logical Keys)**: 原有的 `org_id`, `project_id`, `product_id` 等业务键降级为逻辑标识，重命名为 `org_code`, `project_code`, `product_code` 等，并设置 `UNIQUE INDEX`，仅用于数据导入时的匹配。
- **命名公约 (Naming Convention)**:
    - 后缀 `_id`: 专指指向物理 PK 的外键（BigInt/UUID）。
    - 后缀 `_code`: 专指业务逻辑编码（String），如 `cost_center_code`。
- **MDM 重构同步规程 (Schema Evolution Protocol) [MANDATORY]**:
    - 任何涉及到 MDM 核心表（`mdm_*`）物理主键或逻辑主键（`code` vs `id`）的重构，**必须同步审计并更新**所有相关的初始化与导入脚本 (`scripts/init_*.py`, `scripts/import_*.py`)。
    - 脚本中严禁直接将业务编码（String）赋值给整数型外键字段。必须实现先查询（Resolve）业务码获取物理 ID（Integer），再执行赋值的闭环逻辑。

### 5.2 审计与安全性 (分层要求)
    - **MDM 层 (`mdm_*`)**: 强制继承 `TimestampMixin`（`created_at`, `updated_at`）+ `SCDMixin`（`is_deleted`, `is_current`, `effective_from/to`）。SCD 机制已覆盖软删除与版本追踪。
    - **系统层 (`sys_*`)**: 强制继承 `TimestampMixin`。RBAC 关联表（如 `sys_user_roles`, `sys_role_menu`）应至少包含 `created_at`，以支持安全审计。
    - **插件层 (`{source}_*`)**: 不强制继承 `TimestampMixin`。插件模型的 `created_at`/`updated_at` 保留**源系统 API 返回的时间语义**（如 MR 在 GitLab 的创建时间），不与系统入库时间混淆。生命周期由 `sync_status` 管理。
    - **`created_by` (操作人)**: 不全局强制。仅在**存在用户交互**的业务模块（如 Service Desk `sd_*`）按需添加。自动化同步写入的数据通过 `correlation_id` 和 `sys_sync_logs` 追踪来源。
    - **`correlation_id` (追踪标识) [MANDATORY]**: 所有后台同步相关的 Staging 表 (`stg_raw_data`) 和日志表 (`sys_sync_logs`) 必须包含此字段，以便在 1000+ 项目并行时进行全链路链路还原。
    - **软删除**: 严禁物理删除生产数据。MDM 层通过 `SCDMixin.is_deleted` 实现；插件层通过 `sync_status='DELETED'` 标记源端已消失的实体。
- **数据一致性与性能**: 
    - 关联表必须定义 `UniqueConstraint` 复合索引防重复。
    - 指标结果表必须建立针对时间维度的索引。
    - **插件层索引策略 (Plugin Index Policy)**:
        - **外键字段必建索引**: PostgreSQL 不会自动为 FK 创建索引。所有 `ForeignKey` 列必须显式添加 `index=True`，否则 JOIN 和 CASCADE DELETE 会触发全表扫描。
        - **高频查询字段建索引**: `state`/`status`（列表筛选）、`created_at`/`merged_at`/`committed_date`（时间范围聚合、DORA 指标计算）等高频 WHERE/ORDER BY 字段。
        - **不盲目加索引**: 枚举值极少的字段（如 `environment` 仅 prod/staging，选择性差）或查询频率低的字段不加索引，避免无收益的写入代价。
    - **N+1 问题**: 查询关联对象时必须显式使用 `.options(joinedload(...))`。
    - **批量处理**: 
        - **读**: 大数据集查询必须使用 `yield_per(1000)` 或分页游标。
        - **写**: 插件同步逻辑强制使用 `bulk_insert_mappings`，严禁循环单条 `db.add()`。
- **连接池管理 (Connection Pool) [MANDATORY]**:
    - 数据库连接必须通过**应用级连接池** (`create_engine` 的 `pool_size` + `max_overflow`) 管理。Worker / Scheduler 进程启动时创建**唯一的** `engine` 实例，每个任务从池中借用 Session，处理完归还。
    - **严禁**在循环或回调函数中反复调用 `create_engine()`，否则将导致 PostgreSQL 连接耗尽。
    - 推荐配置：`pool_size=5, max_overflow=10, pool_pre_ping=True`（自动检测断连并重建）。
- **SCD Type 2**: 组织、产品、团队主数据采用慢变维，追踪“历史时刻的负责人”及“当时的组织归属”。
- **唯一键与 SCD 冲突处理 [MANDATORY]**: 
    - 若表内存在业务主键的 `Unique` 约束（如 `mdm_organizations.org_id`），在执行 GetOrCreate 或 SCD 更新前，**必须**去除 `is_current=True` 的过滤条件进行全局查询。
    - 否则，INSERT 操作将由于“看不见”历史记录 (`is_current=False`) 而触发物理唯一冲突。
- **组织架构模式**:
    - **层级 (Hierarchy)**: 公司(Root) -> 中心(Center) -> 部门(Dept)，不再使用 `SYS-` 体系节点。
    - **属性 (Attribute)**: 体系 (Business Line) 作为 `Organization` 的 `business_line` 字段存储，支持跨体系的部门归属。


## 6. 前端设计与组件化 (Frontend Design)
> 🎨 **最高行动指令**：所有前端样式与组件开发，必须严格遵循 [`docs/frontend/CONVENTIONS.md`](docs/frontend/CONVENTIONS.md)。任何与该文档冲突的 UI 实现均视为 Bug。

- **Apple Style 规范**: 强制使用预定义的 CSS 变量（如 `--glass-bg`, `--primary-color`），严禁硬编码 Hex 颜色值。
- **组件工程**: 优先使用 Web Components (Shadow DOM) 实现高内聚组件（如搜索框、卡片）。
- **通信机制**: 跨组件通信通过 `CustomEvent` 实现，严禁随意污染全局 `window` 命名空间。


## 7. 数据建模与 dbt (Data Transformation)
> 📘 **开发指南**: 详细的模型开发手册及代码模式请参见 [`docs/guides/DBT_MODELING_GUIDE.md`](docs/guides/DBT_MODELING_GUIDE.md)。

- **分层逻辑**: 
    | 层级 | 前缀 | 说明 |
    | :--- | :--- | :--- |
    | **Staging** | `stg_` | 原始数据清洗，1:1 映射源表，仅字段重命名与类型强制。 |
    | **Intermediate** | `int_` | 中间转换，跨源关联与过滤。 |
    | **Marts (维度)** | `dim_` | 业务维度表，描述性属性。 |
- **ID 归一化与自愈协议 (Normalization & Self-Healing) [MANDATORY]**:
    - **名称对齐优先**: 在 `int_` 层必须建立 `int_org_normalization` 模型。对于 `zentao_dept_xxx` 等非标 ID，必须通过名称（Name）对齐回填为 HR 规范 ID 或业务中文术语，严禁在报表层暴露原始源系统 ID。
    - **SCD2 历史自愈**: 身份主数据 (`int_golden_identity`) 必须实现基于 SCD2 历史版本的字段回溯逻辑。当当前记录属性（部门/工号）缺失时，自动回滚寻找历史版本中的最近非空值填充。
    - **置信度溯源**: 合并后的记录必须包含 `attribution_source`，标注数据是来自“HR官网”、“归一化映射”还是“历史自愈”。
    | **Marts (事实)** | `fct_` | 业务事实表，度量指标，直接对接报表层。 |
- **源表管理**: 所有原始表必须在 `sources.yml` 中声明，包含 database, schema, table 完整路径。
    - **新鲜度 (Freshness)**: 核心 Source 表必须配置 `freshness` 检查（如:warn_after: {count: 24, period: hour}）。
- **元数据 (Metadata)**: 核心 Marts 模型必须在 `meta` 字段中标记 `owner` 和 `domain`，以便 DataHub 采集。
- **质量哨兵**: 所有模型在 `schema.yml` 必须定义 `unique` 和 `not_null` 测试，关键指标使用 Singular SQL Tests 校验。

### 7.3 dbt 性能与类型守卫 (Performance & Type Safety) [NEW]
- **JSONB 强类型转换**: 从 `JSONB` 提取数值字段进行 `numeric` 转换时，必须执行 `trim(both '"' from field)` 以清除潜在的字面量双引号。结合 `nullif(..., '')` 过滤空字符串，并确保 `coalesce` 兜底。
- **ID 语义一致性 (String IDs)**: 所有跨源关联的业务主键（Master IDs/Entity IDs）在 dbt 语义层强制统一为 `String (character varying)` 类型。严禁在中间层混用 `Integer` 与 `String` 导致关联报错。
- **Staging 透明度**: Staging 模型必须完成所有字段语义对齐（如 `ncloc` -> `lines_of_code`）。严禁在 `int_` 或 `fct_` 层继续直接使用源系统的非标缩写。
- **并发控制**: 在资源受限环境执行 `dbt build` 时，必须通过 `--threads 1` 或环境变量限制并发，防止数据库锁冲突 (Deadlock) 或内存溢出导致的挂起。

### 7.4 BI 与可视化平台 (BI & Visualization) [NEW]
- **平台选型 (Platform Selection)**:
    - **Streamlit (已集成 ✅)**: 核心 BI 交互平台。用于轻量级、交互式数据应用开发，特别是涉及 Python 逻辑的动态看板。
    - **Superset**: 企业级可视化大盘，用于处理大规模 SQL 聚合报表。
    - **Metabase**: 用于业务侧自服务查询 (Self-service BI) 与快速简单看板搭建。
- **数据源接入**: 所有平台必须统一接入 `PostgreSQL` 的 Marts 层 (`rpt_*` 或 `fct_*` 模型)，严禁越过 dbt 直接查询 Staging 表。


## 8. 运维流程与生命周期 (DevOps Ops)

- **部署模式**: 
    - `make deploy`: 本地快速验证部署。支持基础镜像 Nexus 回退机制 (Nexus -> Docker Hub)。
    - `make package`: 生成镜像存档 `devops-platform.tar`。
    - `make deploy-offline`: 生产/隔离环境一键镜像加载并启动。
- **镜像加速与回退**: 项目支持通过 `NEXUS_DOCKER_REGISTRY` 配置私有镜像存储加速。在 `make build` 或 `make package` 时，系统会优先尝试从该私服拉取并打标 (tag) 核心基础镜像 (`python`, `postgres`, `rabbitmq`)，失败则自动回退至官方源。
- **健康检查 (Healthcheck Resilience) [MANDATORY]**: 
    - 所有容器必须定义 `healthcheck`。对于 RabbitMQ、Postgres 等启动较慢的基础设施，`retries` 必须设为不少于 **60** 次，且配置 `start_period`。
    - 针对低配环境，必须显式限制内存/磁盘水位（如 `RABBITMQ_VM_MEMORY_HIGH_WATERMARK_RELATIVE=0.7`），防止误报导致的重启风暴。
- **内网/私服构建规范 (Private Registry Compatibility) [MANDATORY]**:
    - 为适配离线或受限网络，Dockerfile 严禁硬编码外部公共镜像地址。核心工具（如 `uv`）必须利用 `COPY --from` 与 Makefile 中的本地打标机制从 **NEXUS 镜像仓库**提取。
    - 镜像构建阶段必须通过 `ARG` 支持 `UV_IMAGE` 和 `PIP_INDEX_URL` 的注入。
    - 在 Docker 内部安装 Python 包时，必须配合 `--trusted-host` 解决内网 HTTP 私服的认证与安全提示问题，确保“一键内网构建”能力。
- **异步任务 (RabbitMQ)**:
    - **队列分离 (Queue Isolation) [MANDATORY]**: 每个数据源 (Plugin) 必须拥有独立的 RabbitMQ 队列，命名公约为 `{source}_tasks`（如 `gitlab_tasks`, `zentao_tasks`, `sonarqube_tasks`）。**严禁**将多个数据源的任务混入同一队列，防止高频数据源（如 GitLab 1000+ 项目）的任务洪泛 (Flood) 饿死低频但高优先级的数据源（如 ZenTao）。
    - **动态路由与 SSOT**: `MessageQueue.publish_task()` 根据任务 payload 中的 `source` 字段自动路由到对应队列。队列名称列表应从 `PluginRegistry.list_sources()` 动态生成（格式 `{source}_tasks`），Registry 是队列名称的**唯一事实来源 (SSOT)**，严禁在 MQ 模块中硬编码队列列表。
    - **公平消费 (Fair Dispatch)**: Worker 使用 `prefetch_count=1` 以轮询方式同时监听所有已注册队列，确保各数据源获得公平的处理时间片。
    - **幂等性**: `BaseWorker.process` 方法必须实现幂等，处理前校验资源状态，防止重复消费产生脏数据。
    - **失败补偿**: 关键任务配置死信队列 (DLQ)，异步调用通过 `try-except` 捕获异常并记录详细上下文。
    - **调度纪律**:
        - Scheduler 在推送任务前必须校验目标实体的 `sync_status`，处于 `SYNCING` 或 `QUEUED` 状态的实体严禁重复入队，防止队列无限膨胀。
        - **调度限流 (Scheduling Throttle)**: 单轮调度周期内，每个数据源推送的任务数必须设置**上限**（如每次最多 50 个），防止一次性灌满队列。
        - **独立调度周期**: 不同数据源应支持独立的同步间隔配置（如 GitLab 10min、ZenTao 30min），而非共用单一 `SYNC_INTERVAL_MINUTES`。
- **Worker 韧性 (Worker Resilience)**:
    - **自动重连 (Reconnect with Backoff)**: MQ 连接断线时，Worker 必须实现指数退避重连，而非直接崩溃退出。最大重试间隔不超过 60 秒。
    - **容器重启策略**: Docker Compose 中所有长驻服务 (`worker`, `scheduler`) 必须配置 `restart: unless-stopped`，确保进程意外退出后自动恢复。
    - **优雅停机 (Graceful Shutdown)**: Worker 进程必须捕获 `SIGTERM` 信号，确保当前正在处理的任务完成后再退出，严禁在任务执行中途被强制终止导致数据不一致。


## 9. 测试与质量门禁 (Testing)
- **覆盖率目标**: 核心模块 (`core/`, `models/`) >= 80%，插件模块 >= 60%。

### 9.1 测试目录分层规范 (Test Directory & Hierarchy) [REVISED]
为防止测试代码腐化，严格遵循以下物理结构。**严禁**跨层级存放脚本（如在 unit 中存放 selenium 脚本）。

| 层级 | 目录路径 | 职责定义 | 外部依赖 | 默认状态 |
| :--- | :--- | :--- | :--- | :--- |
| **Unit** | `tests/unit/` | 验证纯业务逻辑、Service 层、Helper。 | **禁止**。必须 100% Mock。 | **必选 (Fast)** |
| **Integration (API)** | `tests/integration/api/` | 验证 Router -> Service -> DB 的契约。 | **允许**。仅限 `sqlite:///:memory:`。 | **必选 (Internal)** |
| **Integration (UI)** | `tests/integration/ui/` | 验证前端 DOM -> 后端 API 的端到端。 | **必须**。Selenium / Playwright。 | **可选 (Slow)** |
| **E2E / System** | `tests/e2e/` | 跨服务大周期验证（完整容器链）。 | **必须**。独立 Compose 环境。 | **发布准入** |

- **隔离原则**：集成测试必须进一步划分为 `api` 和 `ui` 子目录。Selenium/浏览器相关逻辑**强制**放入 `integration/ui`。

### 9.2 测试原子性与准入原则 (Criteria) [MANDATORY]
1.  **100ms 准则**: 单个 Unit Test 文件执行时间严禁超过 100ms。
2.  **超时熔断 (Timeout)**: 每个测试用例由 `pytest-timeout` 强制守护，上限为 **30s**。超过此阈值的任务必须被物理杀死。
3.  **Windows 性能守卫**: 
    - 为规避 Windows 下频繁建表/删表的 I/O 阻塞，集成测试的数据库 Engine 必须设置为 `scope="session"`。
    - 数据库表（Base.metadata）只需在会话开始时创建一次。
4.  **默认运行策略**: 为保证开发敏捷性，`pyproject.toml` 的 `addopts` 必须默认包含 `-m "not slow"`。所有耗时超过 2s 的脚本必须手动标记为 `@pytest.mark.slow`。
5.  **模型导入警告**: 在 `conftest.py` 中执行 `create_all` 前，必须显式导入所有相关的 `models` 模块，否则 `sqlite` 将因“no such table”报错。
6.  **集成测试依赖级联注入规范 (Dependency Seeding) [MANDATORY]**:
    - Service 层或 API 层的集成测试**严禁**假设数据库中已有现成底数。
    - 任何涉及外键约束的操作（如向 `gitlab_commits` 插入记录），测试 Setup 阶段必须显式创建并 `flush()` 其所有强制关联的父表实体（如 `GitLabProject`），确保测试在 `--reuse-db` 模式下依然具备原子性与幂等性。

### 9.3 Mock 策略与 E2E 规范
- **Mock 策略**: 外部 API 调用 (GitLab, SonarQube) 必须使用 `requests-mock` 或 `pytest-httpx` 隔离。
- **E2E 规范**: 
    - **框架选型**: 新功能模块强制使用 **Playwright** (更快的执行速度、Trace Viewer 调试)。
    - **凭据管理 (Credentials)**:  E2E 测试所需的登录信息（用户名/邮箱、密码）**必须从 `.env` 文件读取**（对应变量：`E2E_TEST_USER_EMAIL`, `E2E_TEST_USER_PASSWORD`）。**严禁猜测、硬编码或自行编造测试凭据**。AI 代理在执行浏览器自动化操作时同样适用此规则——必须先读取 `.env` 获取凭据后再执行登录。
    - **失败诊断**: CI/自动化运行失败时，必须保存 Trace Viewer 档案 (`test-results/`) 及截图。
    - **视觉锚定**: 涉及可视化大屏或核心 UI 组件，必要时使用 `expect(page).to_have_screenshot()`。
- **伴生测试**: 新增功能必须同步提交对应的 `pytest` 脚本。

### 9.4 AI 代理自动测试与验证规范 (AI Agent Auto-Testing & Verification) [NEW]
为确保 AI 生成代码的质量与生产环境一致性，AI 代理必须严格执行以下验证规程：
1.  **强制测试与运行 (Mandatory Test & Run)**：AI 代理在生成或修改逻辑代码后，**必须**自行编写对应的 `pytest` 测试用例并执行验证。
2.  **测试持久化 (Test Persistence)**：**严禁**仅使用 `tmp/` 下的一次性验证脚本作为终态交付。所有核心逻辑（如 Transformer, Service, Algorithms）的验证必须直接在 `tests/unit/` 或 `tests/integration/` 下创建永久性测试文件。
3.  **容器内验证 (Container-In Validation) [MANDATORY]**：所有测试执行**必须**在 Docker 容器内完成（使用 `make test` 或 `docker-compose exec api pytest`），**严禁**在宿主机环境（如 Windows）下进行单纯的 Python 逻辑验证，以确保在 Linux 环境下的完全兼容。
4.  **DoD 增强 (DoD Enhancement)**：在向用户汇报“任务完成”或“验证通过”前，AI 代理必须提供容器内 pytest 运行成功的日志明细，作为交付成果的一部分。


## 10. 异常处理与日志规范 (Error Handling & Logging)
- **统一异常体系**: 
    - **业务异常**: 所有业务逻辑错误必须抛出自定义异常（继承 `BusinessException`），严禁在 Service 层直接抛出 `HTTPException`。
    - **API 错误契约**: 全局拦截器按以下格式返回 JSON：
        ```json
        {
            "code": "业务域_错误标识",     // 如: SD_TICKET_NOT_FOUND
            "message": "用户友好的语义说明", // 如: "未找到ID为123的工单"
            "detail": {"field": "..."}      // 可选排查明细
        }
        ```
- **日志级别准则**:
    - `INFO`: 关键业务流转（如：工单流转、审批通过）。
    - `WARNING`: 可恢复的异常（如：外部 API 重试）。
    - `ERROR`: 系统不可恢复错误，必须包含 Trigger 上下文及完整 Traceback。
- **关联追踪 (Correlation ID) [MANDATORY]**:
    - **产生**: Scheduler 创建同步任务时必须生成 `correlation_id` (UUID)。
    - **传递**: 随 MQ Payload 传递，Worker 消费时提取并实例化 `logging.LoggerAdapter` 进行包裹输出。
    - **持久化**: 链路涉及的所有 Staging 表和 Sync Log 必须落盘此 ID。
    - **排障价值**: 当生产环境出现同步异常时，通过单个 `correlation_id` 即可在日志和数据库中端到端还原一条任务从调度 → 入队 → 消费 → 写库的完整链路。
- **业务指标 (Metrics)**:
    - 关键业务流程必须暴露可量化指标，以便持续监控系统健康度：
        - **同步指标**: 各数据源同步成功率、失败率、平均耗时。
        - **队列指标**: 各队列深度 (pending messages)、消费速率。
        - **数据库指标**: 连接池使用率、慢查询数量。
    - **采集方式**: 优先通过结构化日志聚合（如 ELK / Loki），未来可扩展至 Prometheus 埋点。严禁为了采集指标而引入重量级依赖。
- **命名空间关联**: 日志内容必须包含业务域前缀（如 `[SD]`, `[ADM]`），以便在日志系统中快速过滤。


## 11. 命名全链路对齐 (Naming Alignment)

### 11.1 业务域前缀注册表 (Domain Prefix Registry)
| 业务域 | 前缀 | 说明 |
| :--- | :--- | :--- |
| **Service Desk** | `sd_` | 工单、支持、SLA、知识库 |
| **Administration** | `adm_` | 平台管理、权限、审计、系统配置 |
| **Project Management** | `pm_` | 项目管理、需求、计划、风险 |
| **Testing / Quality** | `qa_` | 测试用例、缺陷预测、质量报告 |
| **Maintenance** | `ops_` | 运维自动化、资源监控、部署流水线 |
| **Report / Dashboard** | `rpt_` | 报表、看板、数据可视化 |
| **System / Infra** | `sys_` | 系统级基础设施、全局配置、健康检查 |

### 11.2 全链路对齐规范 (以 Service Desk 为例)
所有命名遵循：`前缀_资源名_类型` 或 `前缀-资源名-类型` 结构。确保以下层级在命名空间上保持一致，严禁使用 generic (通用) 的名称（如 ticket, user）。

| 层级 | 命名规范 | 示例 |
| :--- | :--- | :--- |
| **数据库表** | `{prefix}_{resource}s` | `sd_tickets` |
| **SQLAlchemy Model** | `{Prefix}{Resource}` | `SdTicket` |
| **dbt 模型** | `stg_{prefix}_{resource}s` | `stg_sd_tickets` |
| **API 路由** | `/api/{prefix}/{resource}` | `/api/sd/tickets` |
| **后端文件 (Router)** | `{prefix}_{resource}_router.py` | `sd_ticket_router.py` |
| **后端文件 (Service)** | `{prefix}_{resource}_service.py` | `sd_ticket_service.py` |
| **测试文件 (Test)** | `test_{prefix}_{resource}_{type}.py` | `test_sd_ticket_api.py`, `test_portal_frontend_ui.py` |
| **前端 CSS Class** | `.{prefix}-{component}` | `.sd-ticket-card` |
| **错误码** | `{PREFIX}_{ERROR_KEY}` | `PM_REQUIREMENT_NOT_FOUND` |

### 11.3 执行原则
- **强制前缀**：所有新功能模块的开发必须先从上表中选取/注册前缀，确保全链路识别度。
- **语义清晰**：前缀后应紧跟具体的资源名。例如，Service Desk 的聚合视图文件应命名为 `sd_support.py`，而具体的单一工单逻辑应为 `sd_ticket_service.py`。
- **去内联化**：前端样式必须使用带前缀的 Class（如 `.sd-search-bar`），配合 CSS 变量（`var(--primary)`）实现风格统一。


## 12. AI 原生协作与共创 (AI-Native Collaboration & Co-Creation)

> **通用原则**：AI 原生协作的 10 大哲学原理（意图驱动、显性上下文、确定性边界、认知局部性、可验证性、反馈环密度、反向对齐、组合式架构、信任但验证、演进式设计）定义在 [`gemini.md` 第十二章](c:/users/netxs/.gemini/gemini.md)。此处仅记录 **本项目特有的** 补充规则。

### 12.0 用户画像与沟通原则 (User Profile & Communication) [NEW]
- **用户定位**: 本项目的主导者（USER）自定义为 **“技术小白” (Technical Beginner)**。
- **沟通要求**: 
    - **降维解析**: 在编写技术方案、实施步骤或解释代码逻辑时，必须使用通俗易懂的类比（如：出厂标签、合格证、身份证等），严禁堆砌纯晦涩的技术术语。
    - **详尽引导**: 每一项操作指令必须包含“为什么这么做”和“小白视角下的预期结果”。
    - **文档化友好**: 所有交付的文档（如 Spike）必须包含 `[小白专区]` 或类似的解说章节。
    - **主动补位**: 遇到底层技术选择时，AI 应提供明确的推荐建议（Recommended），而不是抛出多个复杂选项让用户自行猜测。

### 12.1 本项目验证规范 (Project-Specific Verification)
- **验证前置 (Validation First)**: 任何开发计划必须包含 `[Verification]` 环节。严禁只有开发逻辑而无测试方案的计划汇报。
- **证据驱动状态 (Evidence-Based Status) [NEW]**: 
    - 在更新 `progress.txt` 或回复“当前项目状态/分支”前，**强制**调用 `git branch`、`ls` 或 `docker ps` 等工具进行实时取证。
    - **严禁**基于逻辑推测（如“按规范本应在某分支”）来填写分支名、文件名或服务状态。
    - **Physical Truth Over Logical Consistency**: 物理事实（工具输出）优先级高于逻辑一致性（规范推论）。
- **取证溯源 (Traceability of Status) [NEW]**: 告知进度时，必须在回复或 Commit Message 中隐含/显式对应到本次对话中的工具输出 ID。
- **伴生测试 (Companion Tests)**: 修改代码必须同步产出测试，且测试必须持久化到 `tests/` 目录，严禁在验证后删除。
- **证据交付 (Evidence-Based Delivery)**: 告知任务完成时，必须包含 `Evidence of Testing` 模块，清晰列出执行的验证脚本、命令及结果日志。
- **验证驱动测试**: Agent 在修改核心 `core/` 或 `models/` 代码后，必须主动执行相关模块的集成测试。
- **问答与实现解耦**: 对于“如何实现”或“原理为何”的咨询，严禁在此轮对话中修改代码。必须等待用户依据解释做出进一步指令。

### 12.2 本项目决策卡点扩展 (Project-Specific Decision Checkpoints)
> 通用决策卡点参见 `gemini.md` 四.3「反向交互与澄清」。以下为本项目特有的额外触发条件：

- **硬编码迁移**：将既有代码中的硬编码逻辑（如白名单、阈值）迁移至配置中心。
- **配置项变更**：新增、修改或删除 `settings` 配置，必须对齐“缺省行为策略”与“异常回退逻辑”。
- **抢跑风险 (Premature Action Check)**：涉及配置选择（如 Nexus 是否需要鉴权）时，即便存在“通用做法”，也必须核对是否已获得用户对特定 Option 的明确决策。

### 12.4 AI 自动文档触发规程 (Autonomous Documentation Protocol) [MANDATORY]
为了实现“零提醒”文档治理，AI 代理在侦测到以下**红线时刻 (Trigger Constraints)** 时，必须**主动且无条件**地执行 `/doc-update` 工作流，严禁等待用户指令：

1.  **任务准完工时刻 (The DoD Moment)**：当一个 P0/P1 或 P2 任务完成验证（Verify），准备回复用户“已完成”前。
2.  **知识突变时刻 (The Harvest Moment)**：凡是遇到以下情况，必须立即更新 `lessons-learned.log`：
    - 针对同一个 Bug 进行了 **2 次以上**的尝试（Retry/Debug）。
    - 发现数据源（GitLab/ZenTao）存在**非标 API 行为**或文档描述之外的陷阱。
3.  **架构偏离修复时刻 (The Drift Moment)**：当发现物理文件（如表名、字段名）与规范或预期不符并完成修正后。
4.  **配置/路由定义时刻 (The Setup Moment)**：新增 API Router、修改 `.env.example` 或 `requirements.txt` 后。

**执行准则**：AI 应先执行文档同步，最后在回复中通过 `[Status]: Documentation Synced` 闭环。

### 12.5 会话交接与上下文连续性 (Session Handover & Continuity) [NEW/MANDATORY]
为了解决 IDE 重启或会话切换导致的“记忆断层”，所有 Agent 必须严格执行以下交接协议：

1.  **新会话首条红线 (Cold Start Redline)**：
    - 任何新会话的**第一条回复**，必须首先执行 `/session-handover` 工作流。
    - **严禁**在未确认当前 Git 分支、脏代码状态及 `progress.txt` 进展前直接修改代码。
    - 回复首部必须包含 **📍 会话恢复摘要**，列出：`Branch`, `Status`, `Focus`, `Backlog`。

2.  **原子任务快照 (Atomic Steps in progress.txt)**：
    - `🏗️ 进行中` 的任务必须拆解为 3-5 个原子化的可勾选子任务（Checkbox）。
    - 正在执行的子任务末尾应标注 `(Doing)`，已完成的标注 `(Done)`。

3.  **接力留言 (Handover Memory)**：
    - 每次任务中断或会话结束前，必须在 `progress.txt` 的 `🎯 当前状态` 后追加 `[Handover Memory]`。
    - 内容包括：当前的逻辑死胡同、已尝试失败的方案、下一步建议尝试的 API/函数。

4.  **物理真实高于逻辑推理**：
    - 严禁回答“我记得做完了”。必须通过 `git log`, `git status`, `ls` 的输出作为进度的唯一判定标准。

### 12.3 项目操作速查 (Project Operational Commands)
- **Schema 同步**: 修改模型后必须执行 `make docs` 更新数据字典 `DATA_DICTIONARY.md`。
- **代码自查 (Self-Review Routine)**: 交付前必须运行 `/code-review` 和 `/lint` 流水线。
- **主数据重置**: 需要定向刷新产品、项目或组织架构时，执行 `python scripts/refresh_master_data.py --scope all --force`。


## 13. 分支开发与版本控制规范 (Branching & Versioning)
> 基础 Git 规范（原子提交、Commit Message、Conventional Commits）参见 [`gemini.md` 第四.5 章](c:/users/netxs/.gemini/gemini.md)。以下为本项目的补充规定。

- **强制性开发流程 (Mandatory Branching)**:
    - **硬性约束**: 所有**新功能 (New Feature)**、**重大逻辑变更 (Major Change)**、**架构重构 (Refactoring)** 必须且只能在独立的业务分支上进行开发。严禁直接在 `main` 或 `master` 分支进行提交。
    - **短寿命原则**: 分支生命周期建议不超过 3 天，任务完成后立即合入 `main` 并清理分支。
- **命名公约 (Naming Convention)**:
- **提交质量**: 
    - **原子提交**: 每次 Commit 仅包含一个逻辑变动。
    - **语义化信息**: 提交消息必须包含业务域和动作（例: `feat(sd): 实现工单异步导出`）。
- **合并前检查清单 (Pre-merge Checklist)**:
    > ⚠️ 以下步骤按顺序执行，任一步骤 FAIL 即中止合并。详细可执行步骤见 `.agent/workflows/merge.md`。

    | 序号 | 检查项 | 命令/动作 | 阻断级别 |
    | :--: | :----- | :-------- | :------: |
    | 1 | **Rebase 同步** | `git rebase origin/main` 解决冲突并保持线性历史 | 🔴 BLOCK |
    | 2 | **代码质量 (Lint)** | `make lint` 通过，无格式问题或死代码 | 🔴 BLOCK |
    | 3 | **单元测试** | `make test-local` 全部通过 (本地快速验证) | 🔴 BLOCK |
    | 4 | **容器内测试** | `make test` 在 Docker 内通过 (环境一致性保证) | 🔴 BLOCK |
    | 5 | **容器部署验证** | `make deploy` 通过，健康检查无异常 | 🔴 BLOCK |
    | 6 | **文档同步** | `progress.txt` 已更新；若涉及架构/技术栈变更则同步 `contexts.md` | 🟡 WARN |
    | 7 | **安全自检** | 无硬编码 Secrets；新增依赖无已知 CVE (手动或工具扫描) | 🟡 WARN |
    | 8 | **数据库兼容** | Schema 变更向后兼容 (Add Column → Deploy Code → Drop Old Column) | 🔴 BLOCK |

    **降级策略**: 当外部环境阻塞（如 Docker 网络不通、外部服务器离线）导致步骤 4/5 无法执行时，必须：
    - 在 `progress.txt` 中明确记录阻塞原因和已完成的替代验证。
    - 至少通过步骤 1-3 (Rebase + Lint + 本地单元测试) 后方可有条件合入。
    - 合入后标记为 **待补验证 (Pending Verification)**，后续环境恢复后补执行步骤 4/5。

- **合并策略**: 推荐使用 **Squash Merge**，保持主分支历史简洁。


## 14. 软件交付生命周期 (Software Delivery Lifecycle)

### 14.1 需求工程与追踪 (Requirements Engineering)
- **状态流转**: 需求必须经历 `Draft` (草稿) -> `Review` (评审) -> `Approved` (批准) -> `In Progress` (开发中) -> `Verified` (已验证) -> `Closed` (关闭) 的完整生命周期。
- **可追溯性 (Traceability)**: 所有代码提交 (Commit) 必须在 Message 中关联需求 ID (如 `Ref: #123`)；测试用例必须在注释或装饰器中标注对应的需求点。

### 14.2 设计决策门禁 (Design Gates)
- **RFC 机制** `[Planned]`: P0/P1 级重大功能或架构变更，**严禁直接编码**。必须先产出 RFC (Request for Comments) 文档存入 `docs/design/`，经用户评审通过后方可实施。
- **Schema 评审**: 任何数据库 Schema 变更（特别是涉及数据迁移的）必须经过独立评审，重点审查**向后兼容性 (Backward Compatibility)**。
- **架构决策记录 (ADR)**:
    - ADR 文件存放于 `docs/adr/`，命名格式 `XXXX-决策标题.md`（如 `0001-queue-isolation.md`）。
    - **触发条件**: 任何改变消息拓扑、数据库 Schema 策略、服务边界、新增基础设施组件或引入新的集成模式的决策，必须产出 ADR。
    - **内容结构**: 标题、状态 (Proposed/Accepted/Deprecated)、上下文 (Context)、决策 (Decision)、后果 (Consequences)。
    - **目的**: 为未来的开发者（包括 AI Agent）提供「为什么这样设计」的可追溯记录，避免架构知识断层。

### 14.3 安全架构与权限 (Security Architecture)
- **RBAC 模型**: 严格遵循基于角色的访问控制。默认策略为 `Deny All`，仅按需授予最小权限。
- **安全左移**:
    - **SAST**: 代码提交前必须通过 Lint 与静态分析。
    - **依赖扫描**: 定期检查 `requirements.txt` / `package.json` 中的第三方库是否存在已知 CVE 漏洞。

### 14.4 发布与版本管理 (Release Strategy)
- **语义化版本 (SemVer)**: 严格遵循 `Major.Minor.Patch` 格式。
- **Changelog** `[Planned]`: 每次发布前必须更新 `CHANGELOG.md`，基于 Keep a Changelog 标准记录 `Added`, `Changed`, `Deprecated`, `Fixed`, `Security`。

### 14.5 完工标准 (Definition of Done - DoD)
- **代码层面**: 通过所有 Lint 检查，无死代码，注释清晰且无拼写错误。
- **验证自动化闭环 (Mandatory Automation)**: 
    - **后端任务**: 必须通过所有对应的 `pytest` 单元测试与集成测试，确保逻辑覆盖率。
    - **前端/UI 任务**: 涉及到 UI 重构或交互逻辑变更，**强制开展 E2E 测试** (Playwright)，确保护核心业务链路正常。
- **文档层面 (Document Sync Matrix) [MANDATORY]**:
    - 任何变更必须根据下表完成文档对齐（调用 `/doc-update`）：
        | 变更类型 | 必更新文档 |
        | :--- | :--- |
        | **Bug 修复 / 故障排除** | `progress.txt`, `lessons-learned.log` |
        | **架构调整 / 规范发布** | `contexts.md`, `ADR` (可选) |
        | **模型 (Model/DB) 变更** | `DATA_DICTIONARY.md` (via `make docs`) |
        | **新依赖引入** | `pyproject.toml`, `requirements.txt`, `.env.example` |
        | **日常功能开发** | `progress.txt` |
        | **Spike 探针完成** | `docs/spikes/YYYY-MM-DD_<topic>.md` |
- **任务分级与估时回溯 (Task Level & Estimation Tracking) [NEW]**:
    - 每条任务在 `progress.txt` 中必须标注任务级别（如 `[L2]`），参见 `/task-kickoff` 工作流。
    - L2 及以上任务完成后，在「最近完成」记录中须附带估时对比：`预估 Xh / 实际 Yh`。
    - 偏差超过 50% 的任务，必须在 `docs/lessons-learned.log` 中分析原因（如：范围蔓延、未预见依赖等），用于持续改进估时精度。
- **知识割取与复盘 (Knowledge Harvest) [MANDATORY]**: 凡是遇到需要 2 次以上尝试才解决的问题、或非标 API 陷阱，必须**主动总结**并更新至 `docs/lessons-learned.log`。每次完工汇报前，必须在回复中包含 `Harvest Items` 摘要，否则视为 DoD 未达成。
- **环境卫生清理 (Cleanup on Exit) [MANDATORY]**: 每次完成功能验证或阶段性任务交付前，**必须强制**执行一次 `make clean`。严禁在根目录残留任何调试生成的脚本、临时日志 (.log, .txt, .csv, debug_*.py, traceback.txt)；确保 `git status` 洁净并更新 `progress.txt` 标记 `[Hygiene]: 已清理临时调试文件`。


## 15. 禅道集成规范与元数据对齐 (ZenTao Integration & Metadata)

### 15.1 实体映射策略 (Entity Strategy)
为了解决禅道不同版本间（特别是 20.0+）的层级差异，采用以下映射逻辑：
- **扁平化兼容**: 需求(Story)、缺陷(Bug) 和 任务(Task) 统一映射至 `ZenTaoIssue` 模型。
- **联合主键机制**: 由于禅道内部 ID 空间非全局唯一，主键强制定义为 `(id, type)`，防止不同实体间的 ID 碰撞。
- **层级穿透**: 
    - 禅道的项目集(Program)、项目(Project) 和 执行(Execution) 统一映射至 `ZenTaoExecution` 表。
    - 强制保存 `parent_id` 和 `path` (如 `,1,5,10,`)，支持基于路径的向上汇总（Roll-up）统计。

### 15.2 FinOps 与效能元数据 (FinOps & Metrics)
为支撑成本分摊与流动效率分析，必须完整采集以下元数据：
- **核心工时 (Man-hours)**:
    - `estimate`: 初始预计工时。
    - `consumed`: 累计消耗工时。
    - `left`: 剩余工时。
- **人员对齐 (Identity)**:
    - 采集原始账号的同时，必须通过 `id_mapping` 逻辑回填 `global_user_id`，确保工时能准确归因到部门成本中心。

### 15.3 拓扑关联规范 (Topology Rules)
- **ISSUE_TRACKER**: 通过 `mdm_entity_topology` 将 DevOps 项目关联至禅道的 **Execution (执行)** ID。
- **继承原则**: 支持基于 `path` 的物理继承。若关联了父级项目，其下属所有未单独定义的子执行将自动继承该业务项目归属。

### 15.4 接口特异性与防护规范 (API Quirks & Guardrails) [MANDATORY]
为了应对禅道非标 API 带来的稳定性挑战，所有相关插件开发必须遵循以下防护规则：

- **1. 认证防御 (Auth Resilience)**:
    - **自动刷新与防死循环**: 必须实现 `401` 异常拦截器。检测到会话过期时，自动调用 `client.refresh_token()` 并重试。为了防止配置错误导致的认证无限死循环，重试逻辑必须包含 `is_retry` 状态位，单次请求仅允许触发一次自动刷新重试。
    - **心跳机制**: MQ 连接必须配置 `heartbeat=600`。由于禅道部分复杂查询（如审计日志）耗时较长，需防止 RabbitMQ 误判消费者死锁。
- **2. 数据一致性陷阱 (Data Integrity)**:
    - **ID=0 语义转换**: 禅道常用 `0` 表示空值（如 `plan_id=0`, `module=0`）。入库前必须将 `0` 转换为 `NULL`，严禁直接写入带外键约束的列。
    - **外键容错与资源韧性**: 
        - **子资源韧性 (Sub-resource Resilience)**: 禅道 List API 返回的资源在 Detail API 中可能因权限或物理删除返回 404。对此类非核心子资源（如 executions, actions），Client 应支持 `allow_404` 模式将其降级为空集合处理，Worker 应对各同步阶段建立异常隔离边界，严禁因个别资源报错中断全量任务。
        - **人员降级**: 对于返回非数字 ID 的人员字段（如 `"closed"`, `"removed"`），系统需通过 `UserResolver` 进行降级处理，失败则保留原始字符串，严禁因外键不匹配导致任务崩溃。
- **3. 类型安全防护 (Type Safety)**:
    - **字典对象适配**: 针对部分字段返回 `dict` 对象而非 `string` 的情况，必须在存储前校验并在 `base_client` 或 `worker` 层面进行 `json.dumps` 转换，防止 PostgreSQL 适配器报错。
    - **版本字段映射**: 使用 Pydantic 的 `alias` 机制同时兼容 `id/ID`、`name/title` 等在不同禅道版本/接口中的字段命名差异。
- **4. 性能与限流 (Performance)**:
    - **增量审计扫描**: `actions` (动作日志) 同步必须强制携带 `since` 时间戳，禁止无状态的全量审计抓取。
    - **空值快速返回**: 接口返回 `null` 或 `total: 0` 时应立即终止当前实体的深度抓取。
- **5. 状态映射归一化 (Status Transformer) [NEW]**:
    - 严禁基于禅道原始字符串直接进行业务统计。必须通过 `ZenTaoTransformer` 将 `Story/Bug/Task` 的差异状态映射为平台标准 5 状态（Backlog, InProgress, Testing, Completed, Cancelled）。
    - 插件内部必须维护一个 SSOT 的状态映射配置，并在抓取层完成转换。


## 16. GitLab 集成规范与性能守卫 (GitLab Integration & Guardrails)

### 16.1 性能与“黑洞”防御 (Performance & Limit)
- **同步深度守卫 (Sync Depth Limit) [MANDATORY]**: 首次同步 (Full Sync) 必须显式传递 `since` 参数。默认仅追溯近 365 天的历史记录，严禁对数万 Commit 的仓库进行无限制全量抓取，除非经用户通过 `force_full_history` 标记确认。
- **Diff 解析截断**: 为防止内存溢出，单一文件 Diff 对比严禁超过 1MB。超过阈值的变更仅记录文件路径变更，不再进行代码行级的深度解析。

### 16.2 状态存活性自查 (Liveness Probe)
- **定期僵尸检查 (Zombies Check)**: 增量任务无法感知 GitLab 侧的物理删除。系统必须配置“周级巡检任务”，全量拉取 GitLab Project ID 列表并与本地数据库对比，若本地存在但在源端已缺失，必须将其标记为 `is_deleted=True`且 `sync_status='DELETED'`。


## 17. 全局身份与成本归因规范 (Global Identity & Attribution)

### 17.1 身份对齐优先 (Identity First) [MANDATORY]
- **主键转换原则**: 任何数据源（GitLab, ZenTao, Jira）采集到的人员标识，入库前**禁止**直接使用原始账号（username/email）作为最终业务关联键。
- **强制转换链**: 采集原始账号 -> 调用 `IdentityManager.get_global_id()` -> 映射为统一的 UUID `global_user_id` -> 存入业务表。
- **成本归因**: 只有完成 `global_user_id` 转换的工时或提交记录，方可参与效能度量与成本中心分摊计算。对于无法对齐的“流浪账号”，系统必须通过 `sys_unknown_identities` 表进行挂起并在看板显著提醒。


## 18. 代码质量与 Ruff 规范 (Code Quality & Ruff) [NEW]

### 18.1 统一工具链 (Unified Tooling)
- **核心工具**: 项目全面采用 **Ruff** 作为唯一的静态代码检查 (Lint) 与格式化 (Format) 工具，取代了传统的 Flake8、Black、isort 和 Pylint (部分核心检查已迁移)。
- **配置标准**: 必须遵循根目录下的 `ruff.toml` 配置。
- **命令行标准**:
    - 代码检查: `make lint` (内部执行 `ruff check`)。
    - 自动修复: `make ruff-fix` (执行 `ruff check --fix`)。
    - 代码格式化: `make fmt` (执行 `ruff format`)。

### 18.2 关键编码禁令 (Hard Rules)
- **禁止 Bare Except**: 严禁使用 `except:` 捕获所有异常，必须显式捕获 `Exception` 或更具体的异常类，防止屏蔽系统级信号。
- **禁止环境变量类型混淆**: 使用 `os.getenv` 时，所有默认值必须为**字符串**（如 `"600"` 而非 `600`），并在使用处显式转换。
- **移除无用导入**: 严禁在非 `__init__.py` 文件中残留未使用的导入。
- **行宽限制 (Line Length)**: 默认限制为 **160**。对于超长的 SQL 字符串，若无法拆分，允许在行尾添加 `# noqa: E501` 或保持原样（若全局已忽略）。

### 18.3 完工标准 (DoD) [REVISED]
- **Green Build**: 任何 PR 在合入 `main` 分支前，必须确保本地执行 `make full-gate` 通过。
- **Full Gate 强制卡点**: `make full-gate` 必须涵盖：
    1.  `make lint`: 0 错误输出。
    2.  `make test`: 容器内全量测试（单元+集成）100% 通过。
    3.  `make build`: Docker 镜像构建成功。
- **复杂度与异常**: 如果因架构需求必须引入复杂逻辑导致复杂度超标（PLR 规则），必须报备并在 `ruff.toml` 或行内添加显式忽略原因。

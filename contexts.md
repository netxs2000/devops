# DevOps Platform Project Contexts (Development Constitution)

> **Document Positioning**: This file is the project-specific constitution for **DevOps Platform**.
> General development philosophy, AI collaboration principles, and workflow rules are defined in [`gemini.md`](c:/users/netxs/.gemini/gemini.md) (global rules).
> `gemini.md` = cross-project universal principles. `contexts.md` = project-specific rules. When conflicts arise, this file takes precedence.

## 1. 项目概览 (Overview)
**DevOps Data Application Platform** 是一套企业级研发效能数据底座。它通过插件化架构采集 GitLab, SonarQube, Jenkins, Zentao 等工具链数据，并利用 dbt 进行指标建模，最终通过 Apple Style 的原生前端界面提供看板与追溯能力。

## 2. 核心技术栈 (Technology Stack)
- **后端 (Backend)**: Python 3.12, FastAPI (Router-Service 模式), SQLAlchemy 2.0 (Typed).
- **数据层 (Data)**: PostgreSQL 15, dbt (数据转换层), RabbitMQ (任务分发控制).
- **前端 (Frontend)**: Native JS/CSS (Apple Style Edition), Web Components, 全局变量约束通信.
- **运维 (DevOps)**: Docker Compose, 多阶段镜像构建, 离线 Tar 包部署支持.

## 3. 开发环境与兼容性 (Environment)
- **本地环境**: Windows + Python 3.12 (调试使用 PowerShell `Select-String` 替代 `grep`).
- **容器环境**: Linux + Python 3.9-3.11 (生产镜像基于 Alpine/Debian Slim).
- **路径处理**: 强制使用 `pathlib` 确保跨平台路径兼容。
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

## 5. 数据库开发规范 (Database & SCD)
- **审计与安全性**:
    - **强制字段**: 所有业务模型必须包含审计字段：`created_at` (创建时间), `updated_at` (最后更新), `created_by` (创建人), `is_deleted` (软删除标记)。
    - **软删除**: 严禁物理删除生产数据。所有删除操作必须通过逻辑删除（`is_deleted=True`）实现。
- **数据一致性与性能**: 
    - 关联表必须定义 `UniqueConstraint` 复合索引防重复。
    - 指标结果表必须建立针对时间维度的索引。
    - **N+1 问题**: 查询关联对象时必须显式使用 `.options(joinedload(...))`。
    - **批量处理**: 
        - **读**: 大数据集查询必须使用 `yield_per(1000)` 或分页游标。
        - **写**: 插件同步逻辑强制使用 `bulk_insert_mappings`，严禁循环单条 `db.add()`。
- **SCD Type 2**: 组织、产品、团队主数据采用慢变维，追踪“历史时刻的负责人”及“当时的组织归属”。
- **组织架构模式**:
    - **层级 (Hierarchy)**: 公司(Root) -> 中心(Center) -> 部门(Dept)，不再使用 `SYS-` 体系节点。
    - **属性 (Attribute)**: 体系 (Business Line) 作为 `Organization` 的 `business_line` 字段存储，支持跨体系的部门归属。

## 6. 前端设计与组件化 (Frontend Design)
> 🎨 **最高行动指令**：所有前端样式与组件开发，必须严格遵循 [`docs/frontend/CONVENTIONS.md`](docs/frontend/CONVENTIONS.md)。任何与该文档冲突的 UI 实现均视为 Bug。

- **Apple Style 规范**: 强制使用预定义的 CSS 变量（如 `--glass-bg`, `--primary-color`），严禁硬编码 Hex 颜色值。
- **组件工程**: 优先使用 Web Components (Shadow DOM) 实现高内聚组件（如搜索框、卡片）。
- **通信机制**: 跨组件通信通过 `CustomEvent` 实现，严禁随意污染全局 `window` 命名空间。

## 7. 数据建模与 dbt (Data Transformation)
- **分层逻辑**: 
    | 层级 | 前缀 | 说明 |
    | :--- | :--- | :--- |
    | **Staging** | `stg_` | 原始数据清洗，1:1 映射源表，仅字段重命名与类型强制。 |
    | **Intermediate** | `int_` | 中间转换，跨源关联与过滤。 |
    | **Marts (维度)** | `dim_` | 业务维度表，描述性属性。 |
    | **Marts (事实)** | `fct_` | 业务事实表，度量指标，直接对接报表层。 |
- **源表管理**: 所有原始表必须在 `sources.yml` 中声明，包含 database, schema, table 完整路径。
    - **新鲜度 (Freshness)**: 核心 Source 表必须配置 `freshness` 检查（如:warn_after: {count: 24, period: hour}）。
- **元数据 (Metadata)**: 核心 Marts 模型必须在 `meta` 字段中标记 `owner` 和 `domain`，以便 DataHub 采集。
- **质量哨兵**: 所有模型在 `schema.yml` 必须定义 `unique` 和 `not_null` 测试，关键指标使用 Singular SQL Tests 校验。

## 8. 运维流程与生命周期 (DevOps Ops)
- **部署模式**: 
    - `make deploy`: 本地快速验证部署。
    - `make package`: 生成镜像存档 `devops-platform.tar`。
    - `make deploy-offline`: 生产/隔离环境一键镜像加载并启动。
- **健康检查**: 所有容器定义 `healthcheck`，容器间依赖依赖 `service_healthy` 状态。
- **异步任务 (RabbitMQ)**:
    - **幂等性**: `BaseWorker.process` 方法必须实现幂等，处理前校验资源状态，防止重复消费产生脏数据。
    - **失败补偿**: 关键任务配置死信队列 (DLQ)，异步调用通过 `try-except` 捕获异常并记录详细上下文。

## 9. 测试与质量门禁 (Testing)
- **覆盖率目标**: 核心模块 (`core/`, `models/`) >= 80%，插件模块 >= 60%。

### 9.1 测试目录分层规范 (Test Directory & Hierarchy)
为防止测试代码腐化，严格遵循以下四层物理结构。禁止在 `tests/` 根目录或业务代码目录中直接存放测试文件。

| 层级 | 目录路径 | 职责定义 | 外部依赖 | 运行频率 |
| :--- | :--- | :--- | :--- | :--- |
| **Unit** | `tests/unit/` | 验证单一函数/类/模块的逻辑正确性。 | **严禁**。必须 Mock 所有 DB、网络、文件系统 IO。 | **每次 Commit** (秒级) |
| **Integration** | `tests/integration/` | 验证多模块交互、数据库约束、API 契约。 | **允许**。可使用 `sqlite:///:memory:` 或本地 Docker 服务的 DB/Redis。 | **合并前 (PR Check)** (分级) |
| **E2E** | `tests/e2e/` | 验证端到端业务流程、UI 交互。 | **必须**。需启动完整后端 + 前端服务 (Playwright)。 | **发布前 (Release)** (小时级) |
| **Scripts** | `tests/scripts/` | 辅助性手工验证脚本、造数工具。 | 任意。不计入自动测试覆盖率。 | 按需执行 |

- **命名规范**：所有测试文件必须以 `test_` 开头 (如 `test_auth_service.py`)，确保 `pytest` 自动发现。

### 9.2 测试原子性与准入原则 (Atomicity & Criteria)
测试代码必须视为生产代码同等对待，严格遵守以下原则：

1.  **独立性 (Independence)**: 
    - 每个测试用例 (Test Case) 必须是**自包含**的。
    - **严禁** Test B 依赖 Test A 产生的数据或状态。
    - **严禁** 依赖测试执行顺序 (pytest-randomly 应能随意打乱执行)。

2.  **无状态 (Statelessness)**:
    - **Setup/Teardown**: 必须在 `fixture` 中完成数据准备与清理。
    - **Global State**: 严禁修改全局变量 (Global Variables) 或单例状态而不复原。
    - **DB Isolation**: 集成测试必须通过 Transaction Rollback 或 `sqlite:///:memory:` 保证每个 Case 拥有干净的数据库环境。

3.  **确定性 (Determinism)**:
    - 消除 "Flaky Tests" (时而通过时而失败)。
    - 避免使用 `sleep()` 等待异步操作，必须使用轮询断言 (`wait_for`)。
    - 固定时间/随机种子：涉及时间计算的测试，必须 Mock `datetime.now()`。

4.  **准入标准 (Gate Criteria)**:
    - **Unit Test**: 必须在 **100ms** 内完成单个文件执行。
    - **Integration Test**: 必须兼容 Windows/Linux 双平台路径。
    - **Coverage**: 新增代码必须包含对应的 Unit Test，否则 PR 不予合并。

### 9.3 Mock 策略与 E2E 规范
- **Mock 策略**: 外部 API 调用 (GitLab, SonarQube) 必须使用 `requests-mock` 或 `pytest-httpx` 隔离。
- **E2E 规范**: 
    - **框架选型**: 新功能模块强制使用 **Playwright** (更快的执行速度、Trace Viewer 调试)。
    - **失败诊断**: CI/自动化运行失败时，必须保存 Trace Viewer 档案 (`test-results/`) 及截图。
    - **视觉锚定**: 涉及可视化大屏或核心 UI 组件，必要时使用 `expect(page).to_have_screenshot()`。
- **伴生测试**: 新增功能必须同步提交对应的 `pytest` 脚本。

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
| **前端 CSS Class** | `.{prefix}-{component}` | `.sd-ticket-card` |
| **错误码** | `{PREFIX}_{ERROR_KEY}` | `PM_REQUIREMENT_NOT_FOUND` |

### 11.3 执行原则
- **强制前缀**：所有新功能模块的开发必须先从上表中选取/注册前缀，确保全链路识别度。
- **语义清晰**：前缀后应紧跟具体的资源名。例如，Service Desk 的聚合视图文件应命名为 `sd_support.py`，而具体的单一工单逻辑应为 `sd_ticket_service.py`。
- **去内联化**：前端样式必须使用带前缀的 Class（如 `.sd-search-bar`），配合 CSS 变量（`var(--primary)`）实现风格统一。

## 12. AI 原生协作与共创 (AI-Native Collaboration & Co-Creation)

> **通用原则**：AI 原生协作的 10 大哲学原理（意图驱动、显性上下文、确定性边界、认知局部性、可验证性、反馈环密度、反向对齐、组合式架构、信任但验证、演进式设计）定义在 [`gemini.md` 第十二章](c:/users/netxs/.gemini/gemini.md)。此处仅记录 **本项目特有的** 补充规则。

### 12.1 本项目验证规范 (Project-Specific Verification)
- **验证前置 (Validation First)**: 任何开发计划必须包含 `[Verification]` 环节。严禁只有开发逻辑而无测试方案的计划汇报。
- **伴生测试 (Companion Tests)**: 修改代码必须同步产出测试，且测试必须持久化到 `tests/` 目录，严禁在验证后删除。
- **证据交付 (Evidence-Based Delivery)**: 告知任务完成时，必须包含 `Evidence of Testing` 模块，清晰列出执行的验证脚本、命令及结果日志。
- **验证驱动测试**: Agent 在修改核心 `core/` 或 `models/` 代码后，必须主动执行相关模块的集成测试。

### 12.2 本项目决策卡点扩展 (Project-Specific Decision Checkpoints)
> 通用决策卡点参见 `gemini.md` 四.3「反向交互与澄清」。以下为本项目特有的额外触发条件：

- **身份/实体“模糊带”**：自动化映射（User/Product）置信度非 1.0 时，需对齐“积极关联”还是“保守挂起”策略。
- **命名空间/前缀扩展**：需定义新业务域前缀或非标术语，需核对第 11 章 SSOT 一致性。
- **硬编码迁移**：将既有代码中的硬编码逻辑（如白名单、阈值）迁移至配置中心。
- **配置项变更**：新增、修改或删除 `settings` 配置，必须对齐“缺省行为策略”与“异常回退逻辑”。

### 12.3 项目操作速查 (Project Operational Commands)
- **Schema 同步**: 修改模型后必须执行 `make docs` 更新数据字典 `DATA_DICTIONARY.md`。
- **代码自查 (Self-Review Routine)**: 交付前必须运行 `/code-review` 和 `/lint` 流水线。


## 13. 分支开发与版本控制规范 (Branching & Versioning)
> 基础 Git 规范（原子提交、Commit Message、Conventional Commits）参见 [`gemini.md` 第四.5 章](c:/users/netxs/.gemini/gemini.md)。以下为本项目的补充规定。

- **命名公约 (Naming Convention)**:
    - 功能开发: `feat/{domain}-{feature_name}` (例: `feat/sd-export-csv`)
    - 缺陷修复: `fix/{domain}-{issue_description}` (例: `fix/adm-user-sync`)
    - 架构重构: `refactor/{module}-{target}`
    - 文档同步: `docs/{topic}`
- **短寿命原则**: 分支生命周期建议不超过 3 天，任务完成后立即合入 `main` 并清理分支。
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
- **测试层面**: 单元测试覆盖率达标，相关功能的 E2E 测试通过，且 **测试资产已入库**。
- **文档层面**: `contexts.md`, `project_summary.md` 及 API 文档 (如有变更) 已同步更新。
- **部署层面**: `make deploy` 在容器环境中验证通过，无回滚风险。
- **汇报完成**: 必须附带验证证据日志。


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

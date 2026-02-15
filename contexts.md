# DevOps Platform Project Contexts (Development Constitution)

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

## 4. 核心架构与插件开发 (Architecture)
- **Plugin Factory**: 插件位于 `devops_collector/plugins/`，结构必须包含 `client.py` (API 封装), `worker.py` (异步逻辑), `models.py` (表定义)。
- **Router-Service 模式**: 
    - **Router 层**: 函数申明必须带 `response_model`，严禁直接返回 SQLAlchemy 对象。命名规则：`{Action}{Resource}Request`。
    - **Service 层**: 业务逻辑承载者，多表操作强制使用 `with db.begin():` 包裹。
- **身份治理映射**: 全球唯一 `global_user_id` 连接各系统账号，置信度通过 `IdentityResolver` 算法动态计算。

## 5. 数据库开发规范 (Database & SCD)
- **审计字段**: 业务模型强制包含 `created_at`, `updated_at`, `created_by`, `is_deleted` (软删除)。
- **数据一致性**: 
    - 关联表必须定义 `UniqueConstraint` 复合索引防重复。
    - 指标结果表必须建立针对时间维度的索引。
- **SCD Type 2**: 组织、产品、团队主数据采用慢变维，追踪“历史时刻的负责人”及“当时的组织归属”。
- **组织架构模式**:
    - **层级 (Hierarchy)**: 公司(Root) -> 中心(Center) -> 部门(Dept)，不再使用 `SYS-` 体系节点。
    - **属性 (Attribute)**: 体系 (Business Line) 作为 `Organization` 的 `business_line` 字段存储，支持跨体系的部门归属。

## 6. 前端设计与组件化 (Frontend Design)
- **Apple Style 规范**: 严格遵循 `docs/frontend/CONVENTIONS.md`，强制使用 CSS 变量（`--primary`, `--radius`）。
- **组件工程**: 优先使用 Web Components (Shadow DOM) 实现高内聚组件（如搜索框、卡片）。
- **通信机制**: 跨组件通信通过 `CustomEvent` 实现，严禁随意污染全局 `window` 命名空间。

## 7. 数据建模与 dbt (Data Transformation)
- **分层逻辑**: 
    - `Staging (stg_)`: 1:1 原始映射，仅字段重命名与类型强制。
    - `Intermediate (int_)`: 跨系统关联与过滤。
    - `Marts (dim_/fct_)`: 业务指标与维度表，直接对接报表层。
- **质量哨兵**: 所有模型在 `schema.yml` 必须定义 `unique` 和 `not_null` 测试，关键指标使用 Singular SQL Tests 校验。

## 8. 运维流程与生命周期 (DevOps Ops)
- **部署模式**: 
    - `make deploy`: 本地快速验证部署。
    - `make package`: 生成镜像存档 `devops-platform.tar`。
    - `make deploy-offline`: 生产/隔离环境一键镜像加载并启动。
- **健康检查**: 所有容器定义 `healthcheck`，容器间依赖依赖 `service_healthy` 状态。

## 9. 测试与质量门禁 (Testing)
- **伴生测试**: 新增功能必须同步提交对应的 `pytest` 脚本。
- **E2E 规范**: 新模块强制使用 Playwright，且必须录制失败时的 Trace (可在 `test-results/` 查看)。
- **视觉锚定**: 涉及可视化大屏或核心 UI 组件，必要时使用 `expect(page).to_have_screenshot()`。

## 10. 命名全链路对齐 (Naming Alignment)
- **业务域前缀**: 强制使用 `sd_` (工单), `adm_` (管理), `pm_` (需求), `qa_` (质量), `ops_` (流水线)。
- **错误码**: 返回 JSON 错误必须包含领域前缀（如 `PM_REQUIREMENT_NOT_FOUND`）。

## 11. AI 辅助开发准则 (AI & Autogen)
- **Schema 同步**: 修改模型后必须执行 `make docs` 更新数据字典 `DATA_DICTIONARY.md`。
- **代码自查**: 提交前使用 `make lint` 确保符合 Google Python Style 且无死循环依赖。
- **AI 交互**: Agent 在修改核心 `core/` 代码后，必须主动执行相关模块的集成测试。

## 12. 分支开发与版本控制规范 (Branching & Versioning)
- **命名公约 (Naming Convention)**:
    - 功能开发: `feat/{domain}-{feature_name}` (例: `feat/sd-export-csv`)
    - 缺陷修复: `fix/{domain}-{issue_description}` (例: `fix/adm-user-sync`)
    - 架构重构: `refactor/{module}-{target}`
    - 文档同步: `docs/{topic}`
- **短寿命原则**: 分支生命周期建议不超过 3 天，任务完成后立即合入 `main` 并清理分支。
- **提交质量**: 
    - **原子提交**: 每次 Commit 仅包含一个逻辑变动。
    - **语义化信息**: 提交消息必须包含业务域和动作（例: `feat(sd): 实现工单异步导出`）。
- **合并前置要求**:
    - 合并前必须执行 `git rebase origin/main` 保持历史线性。
    - **强制容器内验证**: 合入前必须执行 `make test` 和 `make deploy` 通过验证。
- **合并策略**: 推荐使用 **Squash Merge**，保持主分支历史简洁业务。

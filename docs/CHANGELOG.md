# 修订记录 (Changelog)

所有对 DevOps Data Application Platform 的重要更改都将记录在此文件中。

## [4.1.0] - 2026-01-08

### 新增 (Added) - v4.1.0

* **生产环境专用配置**: 新增 `docker-compose.prod.yml`，移除代码卷挂载，限制 RabbitMQ 管理端口对外暴露，并添加 `restart: always` 策略，显著提升生产环境的安全性和稳定性。

### 优化 (Improved) - v4.1.0

* **构建速度提升**: 优化 `Makefile` 的 `init` 流程，移除冗余的 `pip install` 步骤（利用 Docker 镜像层已包含依赖的特性），大幅缩短容器启动和初始化时间。
* **傻瓜式部署**: 新增 `deploy.sh` 脚本和 `make deploy-prod` 指令，自动处理环境检查、配置加载与服务启动，降低服务器运维门槛。
* **生产环境加固**: `docker-compose.prod.yml` 全面升级，新增 **日志轮转** (Log Rotation) 防止磁盘爆满，统一配置 **Asia/Shanghai 时区**，并显式注入 RabbitMQ 账号密码，消除安全隐患。
* **部署文档更新**: 同步更新 README 和用户手册，补充生产环境标准部署指南。

## [4.0.0] - 2026-01-06

### 新增 (Added) - v4.0.0

* **GTM 测试管理模型命名规范**: 为了避免 pytest 自动收集模型类导致的冲突，引入 `GTM` (GitLab Test Management) 前缀，将 `TestCase` 重命名为 `GTMTestCase`，`Requirement` 重命名为 `GTMRequirement`，并同步更新了数据库表名。
* **双向关联增强**: 完善了 `User`、`GitLabProject` 与 `GTM` 模型之间的双向 SQLAlchemy 关系定义。

### 优化 (Improved) - v4.0.0

* **认证服务代码质量**:
  * 全面标准化 `auth/services.py` 和 `auth/router.py` 的 Docstrings 为中文 Google 风格。
  * 修复了 `auth/services.py` 中缺失的 `uuid` 导入。
  * 将所有 `datetime.utcnow()` 更新为推荐的 `datetime.now(timezone.utc)` 标准。
* **模型层稳定性**: 完成了 `base_models.py`、`dependency.py` 及插件模型的文档标准化，移除了所有 100+ 处占位符 `TODO`。
* **插件架构清理**:
  * 彻底移除冗余的 `gitlab_sync` 目录，将功能完全过渡到标准化的插件架构。
  * 优化了 `PluginLoader` 的动态加载逻辑，解决了 SQLAlchemy 模型重复定义触发的警告。
  * 增强了 `禅道 (ZenTao)` 同步逻辑的文档标注。
* **集成测试闭环**: 更新并验证了 `test_model_integration.py`，确保在重构后的 GTM 模型命名体系下，14 个核心业务集成场景全部通过。

## [3.9.0] - 2026-01-02

### 新增 (Added) - v3.9.0

* **Dagster 资产编排 (Asset Orchestration)**: 引入 Dagster 作为核心调度引擎，实现了软件定义资产 (SDA)、全链路血缘追踪与精细化资源管理。
* **dbt 高阶分析模型**: 集成 dbt 实现复杂业务逻辑转化，新增研发 ROI 核算、资本化审计跟踪、开发者行为画像等 10+ 核心分析模型。
* **DataHub 数据治理**: 启动 DataHub 集成，实现元数据自动摄取 (PostgreSQL/dbt) 与标准化数据目录管理。
* **SCD Type 2 统一服务**: 实现通用的 `close_current_and_insert_new` 服务函数，支持主数据 (MDM) 的历史版本留存、有效性字段标记与乐观锁机制。
* **MDM 日历主数据**: 新增 `mdm_calendar` 表及自动化初始化脚本，支持跨地域法定节假日与工作日的精准效能核算。
* **AI 增强风险评估**: 集成 AI 分类模型，实现对 Merge Request 的智能风险分级与异常降噪。
* **Great Expectations 质检**: 在 Dagster 流水中嵌入数据质量检查点，确保从存储层到展现层的数据准确性。

### 优化 (Improved) - v3.9.0

* **迭代管理可视化**: 增强 `devops_portal` 迭代看板，支持根据 GitLab 里程碑实时计算任务进度、自动展示进度条与未完成任务结转。
* **API 契约标准化**: 全面完成基于 Pydantic V2 的输入输出 Schema 定义，显著提升了接口调试与前端交互的稳定性。
* **部署架构升级**: 优化 `docker-compose.yml`，集成 Dagster Daemon、Dagit 与 DataHub 相关容器服务。

---

## [3.8.0] - 2026-01-01

### 新增 (Added) - v3.8.0

* **全量数据模型标准化**: 按照 Google Python Style Guide 完成了 11 个核心及插件模型模块的统一重构。
* **调试增强**: 为所有数据模型添加了结构化的 `__repr__` 方法，极大提升了日志审计与开发调试效率。
* **详细业务标注**: 通过 Google Style Docstrings 为 60+ 数据表字段添加了精确的中文业务描述与类型标注。

### 优化 (Improved) - v3.8.0

* **核心主数据解耦**: 合并并重构了 `test_management.py` 与 `dependency.py` 中的重复模型定义。
* **文档同步自动化**: 同步更新了 `DATA_DICTIONARY.md`、`ARCHITECTURE.md` 等全套 13 份核心技术文档。
* **RBAC 模型完善**: 标准化了角色、权限、令牌管理模型的文档说明。

## [3.7.0] - 2025-12-30

### 新增 (Added) - v3.7.0

* **AI 赋能测试生成 (AC-to-Steps)**: 核心服务 `TestingService` 接入 LLM，支持从需求验收标准 (Acceptance Criteria) 自动生成结构化测试步骤。
* **AIClient 依赖注入**: 为 `TestingService` 等核心服务引入依赖注入模式，提升了系统的可测试性和灵活性。

### 优化 (Improved) - v3.7.0

* **Pydantic V2 全面重构**: 将全量 Schema（Auth, Core, TestHub）升级至 Pydantic V2 标准。
  * 使用 `model_config` 和 `ConfigDict(from_attributes=True)` 替换旧版 ORM 模式。
  * 引入 `validation_alias` 实现数据库字段（如 `global_issue_id`）与 DTO（如 `id`）的自动解耦映射。
* **大模型配置标准化**: `config.py` 适配 `[ai]` 节段配置，支持 `api_key` 和 `base_url` 的工业级配置规范。
* **API 分页健壮性**: 在统计 MR、Issue 等关键指标时，强制使用 `get_all=True` 处理全量分页数据，确保统计精度。

---

## [3.6.0] - 2025-12-29

### 新增 (Added) - v3.6.0

* **MDM_LOCATION地理位置主数据表**: 创建符合GB/T 2260国家标准的地理位置主数据表，支持省/市/区县三级层级结构，初始化34个省级行政区划数据。
* **P2实时通知定向推送**: 完善SSE实时通知系统，实现基于业务场景的精准定向推送功能：
  * 质量门禁拦截：定向推送给项目干系人（区域负责人），替代全员广播模式
  * 测试执行失败：自动通知执行者+用例创建者+需求负责人，实现多方协同
  * 需求评审状态变更：实时通知需求提出者（排除评审人自己），闭环反馈
* **干系人查询辅助函数**: 新增 `get_project_stakeholders()`、`get_requirement_author()`、`get_testcase_author()` 三个辅助函数，支持定向通知。
* **地理位置数据初始化脚本**: 提供 `init_mdm_location.py` 脚本，自动创建表结构、初始化省份数据、迁移历史province字段。

### 优化 (Improved) - v3.6.0

* **User模型升级**: 将 `province` 字符串字段升级为 `location_id` 外键，关联mdm_location表，实现规范化地理位置管理。
* **数据过滤逻辑优化**: 调整 `get_province_quality` 和 `get_province_benchmarking` API，使用location对象获取省份信息，兼容location为空的情况。
* **通知元数据增强**: 所有通知消息增加完整的业务上下文元数据（project_id、executor、requirement_id等），提升可追溯性。

## [3.5.0] - 2025-12-20

### 新增 (Added) - v3.5.0

* **内源共创指数 (InnerSource Impact)**: 实现了跨部门技术流动性的量化体系，建立 `view_pmo_innersource_reuse_heatmap` 视图。
* **隐性满意度 (Shadow Satisfaction Index)**: 发布了基于行为指纹的项目交付体验算法，量化 SLA、争议度与返工率。
* **评审民主度与协作熵**: 新增对代码评审质量的正态性分布监控，识别技术垄断风险。
* **架构脆性指数 (Architectural Brittleness Index)**: 建立模型识别高影响力、高复杂度且低覆盖的核心资产风险。
* **计划确定性模型 (Planning Certainty Model)**: 量化团队的估算水准与承诺履行能力，支持识别“高可靠性”团队。
* **“胶水人”贡献模型 (Glue-Person Index)**: 正式上线，旨在量化并奖励开发者在知识布道、流程守护和协作催化方面的隐性贡献。
* **软件供应链流转效率 (Software Supply Chain Velocity)**: 实现对从构建到发布物理路径的量化监控，识别环境间的流转瓶颈。
* **组织依赖透明度 (Organization Dependency Transparency)**: 建立跨部门阻塞识别模型，量化组织脆弱性指数。
* **财务洞察体系 (Finance Analytics)**: 发布六大财务视角的研发效能洞察模型，包括项目盈利能力、里程碑回款健康度、燃烧率预警、技术债务财务量化、外包成本效益分析、研发资本化合规性监控。
* **内控与合规性洞察体系 (Compliance Analytics)**: 发布七大内控与合规性洞察模型，覆盖 SOX 404、ISO 27001、ITIL、GDPR/PIPL 等合规框架要求，包括四眼原则、权限滥用检测、变更管理追溯、敏感数据访问审计、职责分离验证、开源许可证风险、知识产权保护。
* **OWASP Dependency-Check 集成**: 实现完整的开源依赖扫描与许可证合规性管理，包括依赖清单、CVE 漏洞检测、许可证风险评估、SPDX 标准化支持。
* **指标预警阈值配置白皮书 (`METRIC_THRESHOLDS_GUIDE.md`)**: 定义了分阶段（规范、提效、共创）的效能治理红线及其触发行动。

### 优化 (Improved) - v3.5.0

* **PMO 战略方案升级**: 完善了 `PMO_ANALYTICS_PLAN.md` 中关于数据宽表设计与管理意义的详细逻辑说明。

## [3.4.0] - 2025-12-20

### 新增 (Added) - v3.4.0

* **Jira 360° 采集**: 深度集成 Jira API。新增对 `labels`, `fix_versions`, `time_spent`, `original_estimate` 的采集与持久化。
* **依赖追溯 (Dependency Tracking)**: 提取 Jira Issue Links，并在 `traceability_links` 表中建立跨项目阻塞关系。
* **多渠道风险预警引擎**: 新增 `view_pmo_risk_anomalies` 视图。支持通过企业微信、飞书、钉钉进行结构化 Markdown 消息推送。
* **财务投入透明化**: 建立 `labor_rate_configs` 职级费率体系。新增 `view_pmo_project_labor_costs` 视图自动核算人力成本。
* **人员效能画像**: 新增 `view_user_ability_hexagon` 视图，基于产出、质量、协作、响应、广度和持续性六大指标生成“能力六边形”。
* **Schema 版本管理**: 为 `RawDataStaging` 引入 `schema_version` 字段，支持不同 API 版本的共存与平滑采样。

### 优化 (Improved) - v3.4.0

* **GitLab Worker 重构**: 采用 Mixin 模式拆解大型项目逻辑（Commits/MRs/Issues/Pipelines），引入 `Common Utilities` 模块，大幅降低代码冗余。
* **通知架构重构**: 引入 `BaseBot` 抽象基类，提升了告警渠道的可扩展性。
* **文档体系升级**: 全面更新了 `DATA_DICTIONARY.md`, `ARCHITECTURE.md` 等 11 份核心文档。

---

## [3.3.5] - 2025-12-19

### 新增 (Added) - v3.3.5

* **制品库插件 (Artifactory & Nexus)**: 接入 JFrog 与 Nexus API。支持通过 SHA 校验和追踪制品流转。
* **血缘建立**: 支持从二进制制品回溯至 source 项目及 CI 构建任务的完整链路。

### 优化 (Improved) - v3.3.5

* **DORA 指标增强**: 引入交付前置时间 (Lead Time) 的精细化拆解（Coding/Review/Deploy）。
* **生产环境映射**: 支持在 `config.ini` 中自定义生产环境关键词。

---

## [3.3.0] - 2025-12-18

### 新增 (Added) - v3.3.0

* **禅道 (ZenTao) 插件**: 完整支持需求、任务、缺陷及组织的双向同步。
* **身份管理中心 (`IdentityManager`)**: 正式上线跨工具身份自动对齐逻辑。
* **测试管理中心 (Test Hub)**: 增加对 GitLab Test Management 相关脚本与模板的支持。

---

## [3.2.0] - 2025-12-16

### 新增 (Added) - v3.2.0

* **Jenkins 深度采集**: 支持 Job/Build 及触发源（Manual/WebHook）识别。
* **波士顿矩阵分析**: 自动划分明星/瘦狗项目。

---

## [3.1.0] - 2025-12-14

### 新增 (Added) - v3.1.0

* **架构重构 (v3.1)**: 正式引入 **Raw Data Staging (ODS)** 层，确保数据原始性与可重放性.
* **SonarQube 2.0**: 增加了对代码异味详情的采集。

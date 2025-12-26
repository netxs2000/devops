# 修订记录 (Changelog)

所有对 DevOps Data Collector 的重要更改都将记录在此文件中。

## [3.5.0] - 2025-12-20
### 新增 (Added)
*   **内源共创指数 (InnerSource Impact)**: 实现了跨部门技术流动性的量化体系，建立 `view_pmo_innersource_reuse_heatmap` 视图。
*   **隐性满意度 (Shadow Satisfaction Index)**: 发布了基于行为指纹的项目交付体验算法，量化 SLA、争议度与返工率。
*   **评审民主度与协作熵**: 新增对代码评审质量的正态性分布监控，识别技术垄断风险。
*   **架构脆性指数 (Architectural Brittleness Index)**: 建立模型识别高影响力、高复杂度且低覆盖的核心资产风险。
*   **计划确定性模型 (Planning Certainty Model)**: 量化团队的估算水准与承诺履行能力，支持识别“高可靠性”团队。
*   **“胶水人”贡献模型 (Glue-Person Index)**: 正式上线，旨在量化并奖励开发者在知识布道、流程守护和协作催化方面的隐性贡献。
*   **软件供应链流转效率 (Software Supply Chain Velocity)**: 实现对从构建到发布物理路径的量化监控，识别环境间的流转瓶颈。
*   **组织依赖透明度 (Organization Dependency Transparency)**: 建立跨部门阻塞识别模型，量化组织脆弱性指数。
*   **财务洞察体系 (Finance Analytics)**: 发布六大财务视角的研发效能洞察模型，包括项目盈利能力、里程碑回款健康度、燃烧率预警、技术债务财务量化、外包成本效益分析、研发资本化合规性监控。
*   **内控与合规性洞察体系 (Compliance Analytics)**: 发布七大内控与合规性洞察模型，覆盖 SOX 404、ISO 27001、ITIL、GDPR/PIPL 等合规框架要求，包括四眼原则、权限滥用检测、变更管理追溯、敏感数据访问审计、职责分离验证、开源许可证风险、知识产权保护。
*   **OWASP Dependency-Check 集成**: 实现完整的开源依赖扫描与许可证合规性管理，包括依赖清单、CVE 漏洞检测、许可证风险评估、SPDX 标准化支持。
*   **指标预警阈值配置白皮书 (`METRIC_THRESHOLDS_GUIDE.md`)**: 定义了分阶段（规范、提效、共创）的效能治理红线及其触发行动。

### 优化 (Improved)
*   **PMO 战略方案升级**: 完善了 `PMO_ANALYTICS_PLAN.md` 中关于数据宽表设计与管理意义的详细逻辑说明。

## [3.4.0] - 2025-12-20
### 新增 (Added)
*   **Jira 360° 采集**: 深度集成 Jira API。新增对 `labels`, `fix_versions`, `time_spent`, `original_estimate` 的采集与持久化。
*   **依赖追溯 (Dependency Tracking)**: 提取 Jira Issue Links，并在 `traceability_links` 表中建立跨项目阻塞关系。
*   **多渠道风险预警引擎**: 新增 `view_pmo_risk_anomalies` 视图。支持通过企业微信、飞书、钉钉进行结构化 Markdown 消息推送。
*   **财务投入透明化**: 建立 `labor_rate_configs` 职级费率体系。新增 `view_pmo_project_labor_costs` 视图自动核算人力成本。
*   **人员效能画像**: 新增 `view_user_ability_hexagon` 视图，基于产出、质量、协作、响应、广度和持续性六大指标生成“能力六边形”。
*   **Schema 版本管理**: 为 `RawDataStaging` 引入 `schema_version` 字段，支持不同 API 版本的共存与平滑采样。

### 优化 (Improved)
*   **GitLab Worker 重构**: 采用 Mixin 模式拆解大型项目逻辑（Commits/MRs/Issues/Pipelines），引入 `Common Utilities` 模块，大幅降低代码冗余。
*   **通知架构重构**: 引入 `BaseBot` 抽象基类，提升了告警渠道的可扩展性。
*   **文档体系升级**: 全面更新了 `DATA_DICTIONARY.md`, `ARCHITECTURE.md` 等 11 份核心文档。

---

## [3.3.5] - 2025-12-19
### 新增 (Added)
*   **制品库插件 (Artifactory & Nexus)**: 接入 JFrog 与 Nexus API。支持通过 SHA 校验和追踪制品流转。
*   **血缘建立**: 支持从二进制制品回溯至 source 项目及 CI 构建任务的完整链路。

### 优化 (Improved)
*   **DORA 指标增强**: 引入交付前置时间 (Lead Time) 的精细化拆解（Coding/Review/Deploy）。
*   **生产环境映射**: 支持在 `config.ini` 中自定义生产环境关键词。

---

## [3.3.0] - 2025-12-18
### 新增 (Added)
*   **禅道 (ZenTao) 插件**: 完整支持需求、任务、缺陷及组织的双向同步。
*   **身份管理中心 (`IdentityManager`)**: 正式上线跨工具身份自动对齐逻辑。
*   **测试管理中心 (Test Hub)**: 增加对 GitLab Test Management 相关脚本与模板的支持。

---

## [3.2.0] - 2025-12-16
### 新增 (Added)
*   **Jenkins 深度采集**: 支持 Job/Build 及触发源（Manual/WebHook）识别。
*   **波士顿矩阵分析**: 自动划分明星/瘦狗项目。

---

## [3.1.0] - 2025-12-14
### 新增 (Added)
*   **架构重构 (v3.1)**: 正式引入 **Raw Data Staging (ODS)** 层，确保数据原始性与可重放性。
*   **SonarQube 2.0**: 增加了对代码异味详情的采集。

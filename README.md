# DevOps Data Application Platform (研发效能数据应用平台)

![Version](https://img.shields.io/badge/version-4.2.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![PostgreSQL](https://img.shields.io/badge/postgres-13+-blue)

## 📖 项目简介 (Introduction)

**DevOps Data Application Platform** 是一个企业级研发效能数据采集与分析平台。它旨在打破研发工具链（GitLab, SonarQube, Jenkins 等）之间的数据孤岛，将分散的研发数据聚合为有价值的资产。

系统的核心目标是为企业提供：

* **标准化数据模型**: 采用 Google Style 规范重构的高质量数据模型层，全面接入 **dbt (data build tool)** 驱动的现代数据仓库架构，支持深度的 ODS/DW 转换与血缘追溯。
* **企业级 RBAC 2.0 🌟**: 应用新一代基于菜单树的权限模型，支持分布式数据范围 (Data Scope) 过滤与 RLS (行级安全)，保障敏感数据的多租户/多部门隔离。
* **数据校验哨兵 (Data Quality Sentinel)**: 内置基于 dbt 的 Schema 测试、单元测试和业务规则测试，确保核心指标（如 DORA, SPACE）的 100% 准确性。
* **研发效能度量**: 自动计算 DORA 指标（部署频率、变更前置时间等）、SPACE 框架指标及 流动效能 (Flow Efficiency)。
* **测试管理中台 (Test Management Hub)**: 专为 GitLab 社区版设计的轻量级测试管理工具，支持测试用例库、执行追踪、缺陷看板及质量报告。
* **战略决策支持 (ROI)**: 提供波士顿矩阵（明星/现金牛项目识别）和 ROI 投入产出比分析，对接财务合同数据。
* **智能化生成的测试管理 (AI Generative QA)**: 利用 LLM 自动将需求 AC 转化为标准化测试步骤，提升 50%+ 的用例设计效率。
* **Pydantic V2 零拷贝架构**: 全量采用 V2 特性，实现数据库到 DTO 的极速、优雅转换。
* **人才洞察**: 识别高潜人才、技术专家和离职风险。
* **组织效能分析**: 依托企业组织架构，透视各部门的人力投入与产出。

## ✨ 核心特性 (Key Features)

* **统一身份认证 (Unified Identity)**: 自动关联 GitLab 账号与 SonarQube 账号，识别离职员工和外部贡献者。
* **权限与安全管理 🌟**:
  * **RBAC 2.0 架构**: 经典的五表体系（用户、角色、菜单、角色-菜单、用户-角色），支持细粒度按钮级权限。
  * **行级数据隔离 (RLS)**: 基于 `data_scope` 的自动化 SQL 注入过滤，支持“全部、自定义部门、本部门、本部门及以下、仅本人”五大范围控制。
  * **角色继承**: 支持父子角色权限自动聚合，简化大规模组织下的权限管理。
* **测试管理 🌟**:
  * **结构化用例**: 支持预置条件、测试步骤、优先级等结构化数据存储。
  * **执行审计**: 每次执行自动在 GitLab Issue 记录评论，确保持续集成反馈环闭合。
  * **缺陷联动**: 支持从失败用例一键生成 Bug 链接，内置缺陷看板追踪修复进度。
  * **CI/CD 联动**: 实时关联流水线状态，自动捕捉执行时的构建上下文。
  * **一键质量报告**: 导出包含执行详情与缺陷全景分析的结构化 Markdown 报告。
* **多源数据采集 (Multi-Source Collection)**: 集成 **Airbyte** 实现对 **GitLab** (代码/MR/流水线/Issue)、**SonarQube** (质量/问题/技术债)、**Jira** (敏捷管理) 和 **Jenkins** (构建任务/构建历史) 的高性能数据同步。
* **分析数据集市 (Analytics Mart)**: 内置丰富的 SQL 视图，直接生成 DORA、部门记分卡、资源热力图等报表。
* **战略与财务 (FinOps & ROI)**: 支持 **CBS 成本科目管理**、**合同回款对齐** 与 **ROI 成本投入产出分析**，对齐产研与业务。
* **流动效能 (Flow & Cycle Time)**: 自动追踪 Issue 状态流转，量化阻塞时长，提升过程透明度。
* **智能语义 (AI Insights)**: 基于 LLM 自动提取 Commit/MR/Issue 的业务贡献摘要。
* **工程卓越度 (Developer Experience)**: 采集 MR 评审轮次、深度差异分析、加班分布，全方位量化协作质量。
* **合规与风控 (Governance & Risk)**: 监控绕过流程的 Direct Push 和积压的安全漏洞。
* **开源许可证合规 (OSS License Compliance) 🌟**: 集成 OWASP Dependency-Check，自动扫描项目依赖，识别高风险许可证（GPL/AGPL）和 CVE 安全漏洞，支持 SPDX 标准化和 CVSS 评分。
* **模块化预警与通知 (Modular Alerting & Notification) 🌟**: 系统内置了高性能的“多渠道风险预警引擎”，实现从数据洞察到管理动作的闭环：
  * **异常识别**: 定时扫描 `view_pmo_risk_anomalies` 视图，识别异常数据。
  * **多端推送**: 支持 **企业微信 (WeCom)**、**飞书 (Feishu)** 和 **钉钉 (DingTalk)** 的 Webhook 集成。
  * **结构化触达**: 自动生成富文本卡片，包含风险等级颜色标识与责任人 @ 提及功能。
* **断点续传 (Resumable Sync)**: 针对海量数据同步设计，支持意外中断后自动恢复。
* **数据时光机 (Data Time Machine)**: 完整的 Raw Data Staging 层记录，支持基于历史原始数据进行逻辑重演与修复 (Reprocessing)。
* **极致简洁架构 (Refactor)**: 采用微内核 + 插件工厂模型，代码资产完全模块化，核心逻辑与具体数据源解耦。

## 🛠️ 技术栈 (Tech Stack)

* **语言**: Python 3.9+
* **数据库**: PostgreSQL (生产环境推荐)
* **ORM**: SQLAlchemy
* **架构**: ELT (Extract-Load-Transform)，采用 **Airbyte** 进行统一数据抽取 (Extract) 与加载 (Load)，重度依赖 **dbt** 进行数据建模与逻辑编排，辅以 SQL Views 进行实时分析。
* **数据质量**: Great Expectations (v1.10.0) - 用于深度数据质量校验。

## 🚀 快速开始 (Quick Start)

### 1. 环境准备

确保已安装 **Docker** 和 **Docker Compose**。本项目实现了完全容器化部署，无需本地配置 Python 环境。

> **🇨🇳 中国大陆用户特别提示**:
> 由于网络原因，拉取 Docker Hub 镜像可能会失败。本项目提供了自动配置脚本：
>
> ```bash
> # 自动配置国内镜像加速 (需要 root 权限)
> sudo bash scripts/setup_china_mirrors.sh
> ```
>
> 此外，`Dockerfile` 已默认集成了阿里云 (Debian) 和清华源 (PyPI) 加速，`deploy.sh` 脚本在部署时也会自动检测网络状况并提示优化。

### 2. 配置说明

本项目采用 **环境驱动配置 (Environment-Based Configuration)**，完全遵循 12-Factor App 原则。所有配置（基础设施 + 业务逻辑）均通过环境变量管理。

```bash
# 1. 复制示例配置
cp .env.example .env

# 2. 编辑 .env 文件
#    - 基础设施: 设置 DB_PASSWORD, RABBITMQ_USER 等
#    - 业务集成: 设置 GITLAB__URL, SONARQUBE__TOKEN 等 (注意使用双下划线 __ 处理层级)
```

### 3. 多环境部署指南 (Deployment Modes)

系统支持三种标准的构建与部署模式，请根据您的使用场景选择：

| 模式 | 适用场景 | 配置文件 | 镜像策略 | 包含组件 |
| :--- | :--- | :--- | :--- | :--- |
| **A. 开发环境** | 本地编码/调试 | `docker-compose.yml` | 本地构建 + Dev依赖 | API, dbt, Streamlit, **Pytest, Black** |
| **B. 生产环境** | 在线服务器 | `docker-compose.prod.yml` | 纯净精简镜像 | API, dbt, Streamlit, **DataHub CLI** |
| **C. 离线环境** | 内网隔离环境 | `docker-compose.prod.yml` | `tar` 包导入 | 同生产环境 (**含 DataHub 独立镜像**) |

#### A. 开发环境 (Development)
>
> 适用于开发人员本地使用，支持代码热重载，并自动安装测试框架。

```bash
make deploy
```

* **动作**: 停止旧容器 -> 构建镜像 -> 启动服务 -> **安装开发依赖 (`requirements-dev.txt`)** -> 初始化数据。
* **依赖**: 容器启动后会自动执行 `pip install` 安装 `pytest`, `black`, `flake8` 等工具。
* **验证**: 运行 `make test` 确保开发环境正常。

#### B. 生产环境 (Production)
>
> 适用于可联网的生产服务器。使用精简镜像，剥离了编译器和开发工具，确保安全与稳定。

```bash
# 方式 1: 使用脚本 (推荐)
./deploy.sh

# 方式 2: 使用 Make 命令
make deploy-prod
```

* **动作**: 停止旧容器 -> 构建生产镜像 (`--target release`) -> 启动服务 -> 初始化数据。
* **特点**: 自动配置 `restart: always`，日志滚动策略，以及时区同步。

#### C. 离线环境 (Offline / Air-gapped)
>
> 适用于银行/军工等无法连接外网的敏感环境。

**步骤 1: 在有网机器上打包**

```bash
make package
```

* **产物**: 生成 `devops-platform.tar` 文件（约 800MB+）。
* **包含**:
    1. `devops-platform:latest`: 核心应用镜像。
    2. `devops-platform-datahub:latest`: 独立 DataHub 采集器镜像。

**步骤 2: 上传至离线服务器并部署**
将 `tar` 包、`Makefile`、`docker-compose.prod.yml` 和 `.env` 上传至服务器。

```bash
make deploy-offline
```

* **动作**: 加载 Docker 镜像 -> 启动服务 (跳过构建) -> 初始化数据。

部署完成后，服务将运行在后台：

* **API 服务**: <http://localhost:8000>
* **RabbitMQ 管理后台**: <http://localhost:15672> (用户/密码: guest/guest)

### 4. 常用运维命令

所有操作均封装在 `Makefile` 中，自动在容器内执行，确保环境一致性。

```bash
# 查看实时日志
make logs

# 运行测试用例
make test

# 手动触发全量同步
make sync-all

# 停止服务
make down
```

### 5. 部署分析视图

初始化过程 (`make deploy`) 已自动包含基础数据初始化。如需更新 SQL 分析视图：

```bash
# (高级) 手动进入数据库容器执行 SQL
docker-compose exec -T db psql -U postgres -d devops_db -f /app/devops_collector/sql/PROJECT_OVERVIEW.sql
# ... 其他视图同理
```

## 📂 项目结构 (Project Structure)

```text
devops_collector/     # 数据采集核心 (Python)
├── models/             # 基础物理表定义 (SQLAlchemy)
├── sql/                # 传统分析视图定义
dbt_project/          # 现代数仓建模层 (dbt)
├── models/             # 数仓模型 (Staging/Int/Marts)
├── tests/              # 业务规则自定义测试
└── dbt_project.yml     # dbt 项目配置
```

## 🌟 最新特性 (New Features v4.0.0)

本版本引入了基于 **GitPrime**, **DORA**, **SPACE**, **Flow Framework** 四大理论的下一代效能度量体系。

* **ELOC 2.0 (Equivalent Lines of Code)**: 告别单纯的“代码行数”。引入 **Impact Score** (对老代码修改加权) 和 **Churn Rate** (对近期重写代码降权)，还原代码真实价值。
* **Flow Framework (价值流管理)**: 自动将工作项分类为 **Feature**, **Defect**, **Debt**, **Risk**，可视化展示研发资源的配比与价值流动速率。
* **SPACE 框架 (多维平衡)**: 从 **S**atisfaction (心情打卡), **P**erformance (DORA), **A**ctivity, **C**ommunication, **E**fficiency 五个维度构建平衡记分卡。
* **研发体验脉搏 (DevEx Pulse)**: 内置心情打卡挂件，实时捕捉团队士气波动。
* **代码热点雷达 (Code Hotspots)**: 基于 **Michael Feathers** 理论的 F-C 象限分析，通过“复杂度 vs 变更频率”自动识别高危技术债务。
* **DORA 金标准看板**: 引入行业对标评级 (High/Elite/Low)，让效能改进有据可依。

## 📚 文档 (Documentation)

* **[架构技术白皮书 (ARCHITECTURE_WHITE_PAPER.md)](./docs/design/ARCHITECTURE_WHITE_PAPER.md)**: 🚀 **CORE** 深入解读“主数据 (MDM) + 现代数仓 (dbt)”的六层深度重构架构。
* **[度量体系白皮书 (METRICS_ARCHITECTURE.md)](./docs/design/METRICS_ARCHITECTURE.md)**: 🔥 **NEW** 详解 ELOC 2.0、DORA、SPACE、Flow 等核心算法与实现逻辑。
* [用户手册 (PROJECT_SUMMARY_AND_MANUAL.md)](./docs/PROJECT_SUMMARY_AND_MANUAL.md): 功能说明与操作指南。
* [数据字典 (DATA_DICTIONARY.md)](./docs/api/DATA_DICTIONARY.md): 表结构定义。
* [API 接口参考 (API_REFERENCE.md)](./docs/api/API_REFERENCE.md): RESTful API 接口文档。
* [部署与运维 (DEPLOYMENT.md)](./docs/guides/DEPLOYMENT.md): 环境配置与部署指南。
* [故障排查 (TROUBLESHOOTING.md)](./docs/guides/TROUBLESHOOTING.md): 常见问题解决方案。
* **[RBAC 2.0 权限设计 (RBAC_DESIGN_PROPOSAL.md)](./docs/design/RBAC_DESIGN_PROPOSAL.md)**: 🛡️ **SECURITY** 详解新一代基于“角色-菜单-数据范围”的权限控制体系。
* [安全政策 (SECURITY.md)](./docs/SECURITY.md): 漏洞报告与安全最佳实践。

## 📂 看板与视图 (Analytics Mapping)

系统通过 Streamlit 看板与底层 SQL 视图的严格映射，实现了可维护的分析层架构。

| Dashboard Page | SQL Definition (`devops_collector/sql/`) |
| :--- | :--- |
| `1_Gitprime.py` | `Gitprime.sql` |
| `2_DORA_Metrics.py` | `dws_project_metrics_daily.sql / fct_dora_metrics.sql` (dbt) |
| `16_Michael_Feathers_Code_Hotspots.py` | `Michael_Feathers_Code_Hotspots.sql` |
| `17_SPACE_Framework.py` | `dws_space_metrics_daily.sql` (dbt) |
| `18_Value_Stream.py` | `dws_flow_metrics_weekly.sql` (dbt) |

# DevOps Data Collector (研发效能数据采集器)

![Version](https://img.shields.io/badge/version-3.7.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![PostgreSQL](https://img.shields.io/badge/postgres-13+-blue)

## 📖 项目简介 (Introduction)

**DevOps Data Collector** 是一个企业级研发效能数据采集与分析平台。它旨在打破研发工具链（GitLab, SonarQube, Jenkins 等）之间的数据孤岛，将分散的研发数据聚合为有价值的资产。

系统的核心目标是为企业提供：
*   **研发效能度量**: 自动计算 DORA 指标（部署频率、变更前置时间等）、SPACE 框架指标及 **流动效能 (Flow Efficiency)**。
*   **GitLab 测试管理中台 (Test Management Hub)**: 专为 GitLab 社区版设计的轻量级测试管理工具，支持测试用例库、执行追踪、缺陷看板及质量报告。
*   **战略决策支持 (ROI)**: 提供波士顿矩阵（明星/现金牛项目识别）和 **ROI 投入产出比分析**，对接财务合同数据。
*   **智能化生成的测试管理 (AI Generative QA)**: 利用 LLM 自动将需求 AC 转化为标准化测试步骤，提升 50%+ 的用例设计效率。
*   **Pydantic V2 零拷贝架构**: 全量采用 V2 特性，实现数据库到 DTO 的极速、优雅转换。
*   **人才洞察**: 识别高潜人才、技术专家和离职风险。
*   **组织效能分析**: 依托企业组织架构，透视各部门的人力投入与产出。

## ✨ 核心特性 (Key Features)

*   **统一身份认证 (Unified Identity)**: 自动关联 GitLab 账号与 SonarQube 账号，识别离职员工和外部贡献者。
*   **GitLab 测试管理 (Test Hub) 🌟 (New)**: 
    *   **结构化用例**: 支持预置条件、测试步骤、优先级等结构化数据存储。
    *   **执行审计**: 每次执行自动在 GitLab Issue 记录评论，确保持续集成反馈环闭合。
    *   **缺陷联动**: 支持从失败用例一键生成 Bug 链接，内置缺陷看板追踪修复进度。
    *   **CI/CD 联动**: 实时关联流水线状态，自动捕捉执行时的构建上下文。
    *   **一键质量报告**: 导出包含执行详情与缺陷全景分析的结构化 Markdown 报告。
*   **多源数据采集 (Multi-Source Collection)**: 支持 **GitLab** (代码/MR/流水线/Issue)、**SonarQube** (质量/问题/技术债) 和 **Jenkins** (构建任务/构建历史)。
*   **分析数据集市 (Analytics Mart)**: 内置丰富的 SQL 视图，直接生成 DORA、部门记分卡、资源热力图等报表。
*   **战略与财务 (FinOps & ROI)**: 支持 **CBS 成本科目管理**、**合同回款对齐** 与 **ROI 成本投入产出分析**，对齐产研与业务。
*   **流动效能 (Flow & Cycle Time)**: 自动追踪 Issue 状态流转，量化阻塞时长，提升过程透明度。
*   **智能语义 (AI Insights)**: 基于 LLM 自动提取 Commit/MR/Issue 的业务贡献摘要。
*   **工程卓越度 (Developer Experience)**: 采集 MR 评审轮次、深度差异分析、加班分布，全方位量化协作质量。
*   **合规与风控 (Governance & Risk)**: 监控绕过流程的 Direct Push 和积压的安全漏洞。
*   **开源许可证合规 (OSS License Compliance) 🌟 (New)**: 集成 OWASP Dependency-Check，自动扫描项目依赖，识别高风险许可证（GPL/AGPL）和 CVE 安全漏洞，支持 SPDX 标准化和 CVSS 评分。
*   **模块化预警与通知 (Modular Alerting & Notification) 🌟 (New)**: 系统内置了高性能的“多渠道风险预警引擎”，实现从数据洞察到管理动作的闭环：
    *   **异常识别**: 定时扫描 `view_pmo_risk_anomalies` 视图。
    *   **多端推送**: 支持 **企业微信 (WeCom)**、**飞书 (Feishu)** 和 **钉钉 (DingTalk)** 的 Webhook 集成。
    *   **结构化触达**: 自动生成富文本卡片，包含风险等级颜色标识与责任人 @ 提及功能。
*   **断点续传 (Resumable Sync)**: 针对海量数据同步设计，支持意外中断后自动恢复。
*   **数据时光机 (Data Time Machine)**: 完整的 Raw Data Staging 层记录，支持基于历史原始数据进行逻辑重演与修复 (Reprocessing)。
*   **极致简洁架构 (Refactor)**: 采用微内核 + 插件工厂模型，代码资产完全模块化，核心逻辑与具体数据源解耦。

## 🛠️ 技术栈 (Tech Stack)

*   **语言**: Python 3.9+
*   **数据库**: PostgreSQL (生产环境推荐)
*   **ORM**: SQLAlchemy
*   **架构**: ELT (Extract-Load-Transform)，重度依赖 SQL Views 进行业务逻辑计算。

## 🚀 快速开始 (Quick Start)

### 1. 环境准备

确保已安装 Python 3.9+ 和 PostgreSQL 数据库。

```bash
# Clone 项目
git clone <repository_url>
cd devops_collector

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置文件

复制 `config.ini.example` 为 `config.ini` 并填写配置：

```ini
[database]
url = postgresql://user:password@localhost:5432/devops_db

[gitlab]
url = https://gitlab.example.com
token = glpat-xxxxxxxxxxxx

[sonarqube]
url = https://sonar.example.com
token = squ_xxxxxxxxxxxx

[jenkins]
url = http://jenkins.example.com
user = admin
token = j_xxxxxxxxxxxx

[common]
org_name = MyCompany
```

### 3. 初始化系统

运行初始化脚本，自动创建表结构并发现组织架构：

```bash
# 1. 基础数据库与组织架构
python scripts/init_discovery.py

# 2. 财务科目与合同数据 (New)
python scripts/init_cost_codes.py
python scripts/init_labor_rates.py
python scripts/init_purchase_contracts.py
python scripts/init_revenue_contracts.py
```

### 4. 部署分析视图 (关键步骤)

将内置的分析模型 (SQL Views) 部署到数据库：

```bash
# 需确保已安装 psql 或通过数据库客户端执行
psql -d devops_db -f devops_collector/sql/PROJECT_OVERVIEW.sql
psql -d devops_db -f devops_collector/sql/PMO_ANALYTICS.sql
psql -d devops_db -f devops_collector/sql/HR_ANALYTICS.sql
psql -d devops_db -f devops_collector/sql/TEAM_ANALYTICS.sql
```

### 5. 数据采集

建议配置 Crontab 定时运行：

```bash
# 启动调度器 (生成同步任务到 MQ)
python -m devops_collector.scheduler

# 启动 Worker 执行采集 (从 MQ 消费任务)
python -m devops_collector.worker
```

## 📂 项目结构 (Project Structure)

```
devops_collector/
├── models/                # 基础物理表定义 (Tables)
├── sql/                   # 分析视图定义 (Views / Data Mart)
│   ├── PROJECT_OVERVIEW.sql # 项目宽表
│   ├── PMO_ANALYTICS.sql    # 战略与管理视图
│   └── HR_ANALYTICS.sql     # 人才与组织视图
├── plugins/               # 数据源插件
└── scripts/               # 工具脚本
```

## 📚 文档 (Documentation)

*   [**用户手册 (PROJECT_SUMMARY_AND_MANUAL.md)**](./PROJECT_SUMMARY_AND_MANUAL.md): 详细的功能说明与操作指南。
*   [**PMO 分析方案 (PMO_ANALYTICS_PLAN.md)**](./PMO_ANALYTICS_PLAN.md): 战略分析指标的设计思路。
*   [**数据字典 (DATA_DICTIONARY.md)**](./DATA_DICTIONARY.md): 数据库表结构与字段说明。
*   [**需求规格 (REQUIREMENTS_SPECIFICATION.md)**](./REQUIREMENTS_SPECIFICATION.md): 详细的功能需求列表。
*   [**架构设计 (ARCHITECTURE.md)**](./ARCHITECTURE.md): 系统架构说明。

## 📄 许可证 (License)

[MIT](LICENSE)

## 🌟 最新特性 (New Features v3.4.0)
*   **Jira 360° 采集**: 深度解析标签、修复版本、工时预估与实际值、以及 Issue Links 依赖。
*   **多渠道风险预警**: 异常指标自动推送至**企业微信、飞书、钉钉**，风险无处遁形。
*   **财务透明化**: 基于职级费率自动核算研发人工成本，支持项目 ROI 分析。
*   **人才能力六边形**: 自动化生成基于产出、质量、协作等维度的开发者画像。
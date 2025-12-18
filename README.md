# DevOps Data Collector (研发效能数据采集器)

![Version](https://img.shields.io/badge/version-3.2.0-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![PostgreSQL](https://img.shields.io/badge/postgres-13+-blue)

## 📖 项目简介 (Introduction)

**DevOps Data Collector** 是一个企业级研发效能数据采集与分析平台。它旨在打破研发工具链（GitLab, SonarQube, Jenkins 等）之间的数据孤岛，将分散的研发数据聚合为有价值的资产。

系统的核心目标是为企业提供：
*   **研发效能度量**: 自动计算 DORA 指标（部署频率、变更前置时间等）和 SPACE 框架指标。
*   **战略决策支持**: 提供波士顿矩阵（明星/现金牛项目识别）和 ROI 投入产出比分析。
*   **人才洞察**: 识别高潜人才、技术专家和离职风险。
*   **组织效能分析**: 依托企业组织架构，透视各部门的人力投入与产出。

## ✨ 核心特性 (Key Features)

*   **统一身份认证 (Unified Identity)**: 自动关联 GitLab 账号与 SonarQube 账号，识别离职员工和外部贡献者。
*   **多源数据采集 (Multi-Source Collection)**: 支持 **GitLab** (代码/MR/流水线/Issue)、**SonarQube** (质量/问题/技术债) 和 **Jenkins** (构建任务/构建历史)。
*   **数据分析集市 (Analytics Mart)**: 内置丰富的 SQL 视图，直接生成 DORA、部门记分卡、资源热力图等报表。
*   **合规与风控 (Governance & Risk)**: 监控绕过流程的 Direct Push 和积压的安全漏洞。
*   **断点续传 (Resumable Sync)**: 针对海量数据同步设计，支持意外中断后自动恢复。

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
python scripts/init_discovery.py
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
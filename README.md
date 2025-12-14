# DevOps Data Collector (研发效能数据采集器)

## 📖 项目简介 (Introduction)

**DevOps Data Collector** 是一个企业级研发效能数据采集与分析平台。它旨在打破研发工具链（GitLab, SonarQube 等）之间的数据孤岛，通过统一的数据模型和身份认证机制，将分散的研发数据聚合为有价值的资产。

系统的核心目标是为企业提供：
*   **研发效能度量**: 自动计算 DORA 指标（部署频率、变更前置时间等）。
*   **代码质量透视**: 统一管理技术债务、代码覆盖率和千行代码缺陷率。
*   **组织效能分析**: 依托企业组织架构，透视各部门的人力投入与产出。

## ✨ 核心特性 (Key Features)

*   **统一身份认证 (Unified Identity)**: 自动关联 GitLab 账号与 SonarQube 账号，识别离职员工和外部贡献者（虚拟账号）。
*   **多源数据采集 (Multi-Source Collection)**: 插件化架构，目前支持 **GitLab** (代码/MR/流水线/Issue) 和 **SonarQube** (质量/问题)。
*   **企业级组织架构 (Enterprise Hierarchy)**: 支持 "公司 > 中心 > 部门 > 小组" 四级架构，实现精细化管理。
*   **断点续传 (Resumable Sync)**: 针对海量数据同步设计，支持意外中断后自动恢复。
*   **标准数据模型 (Standard Data Model)**: 基于 SQLAlchemy 的规范化 ORM 设计，便于二次开发和 BI 报表接入。

## 🛠️ 技术栈 (Tech Stack)

*   **语言**: Python 3.9+
*   **数据库**: PostgreSQL (推荐)
*   **ORM**: SQLAlchemy
*   **HTTP 客户端**: Requests (带重试机制)
*   **调度**: (可选) Crontab 或 Airflow

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
; 如果是 SQLite (仅测试): sqlite:///devops.db

[gitlab]
url = https://gitlab.example.com
token = glpat-xxxxxxxxxxxx
nop_token = glpat-yyyyyyyyyyyy ; (可选) 备用 Token

[sonarqube]
url = https://sonar.example.com
token = squ_xxxxxxxxxxxx

[common]
org_name = MyCompany
```

### 3. 初始化数据库

运行初始化脚本，自动创建表结构并发现组织架构：

```bash
python scripts/init_discovery.py
```

### 4. 数据采集

运行采集脚本（建议配置为定时任务）：

```bash
# 采集 GitLab 数据
python -m devops_collector.main

# 采集 SonarQube 数据 (需先完成 GitLab 采集以建立项目映射)
python scripts/sonarqube_stat.py
```

### 5. 数据验证

采集完成后，可运行验证脚本检查数据一致性：

```bash
python scripts/verify_logic.py
```

## 📂 项目结构 (Project Structure)

```
devops_collector/
├── config.ini             # 配置文件
├── models/                # 公共数据模型
│   └── base_models.py     # Base, User, Organization, SyncLog
├── plugins/               # 数据源插件
│   ├── gitlab/            # GitLab 采集逻辑
│   └── sonarqube/         # SonarQube 采集逻辑
├── scripts/               # 工具与分析脚本
│   ├── init_discovery.py           # 初始化与组织发现
│   ├── gitlab_user_contributions.py# 个人贡献度计分
│   └── sonarqube_stat.py           # 质量趋势分析
└── DATA_DICTIONARY.md     # 数据字典 (核心文档)
```

## 📚 文档 (Documentation)

*   [**数据字典 (DATA_DICTIONARY.md)**](./DATA_DICTIONARY.md): 详细的数据库表结构与字段说明。
*   [**架构设计 (ARCHITECTURE.md)**](./ARCHITECTURE.md): 系统架构与设计理念说明。

## 🤝 贡献指南 (Contribution)

1.  Fork 本仓库
2.  创建特性分支 (`git checkout -b feature/AmazingFeature`)
3.  提交更改 (`git commit -m 'Add some AmazingFeature'`)
4.  代码风格检查 (遵循 Google Python Style Guide)
5.  推送到分支 (`git push origin feature/AmazingFeature`)
6.  提交 Pull Request

## 📄 许可证 (License)

[MIT](LICENSE)
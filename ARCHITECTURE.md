# 系统架构设计文档 (System Architecture Design)

## 1. 架构概览 (Architecture Overview)

DevOps Data Collector 采用模块化的**ETL (Extract, Transform, Load)** 架构，旨在实现高扩展性、高可靠性和数据的一致性。

系统由四层组成：
1.  **采集层 (Collection Layer)**: 插件化适配器，负责对接不同 API (GitLab, SonarQube, Jenkins)。
2.  **核心层 (Core Layer)**: 负责数据清洗、实体关联、身份归一化、任务分发 (RabbitMQ) 和持久化。
3.  **存储层 (Storage Layer)**: 关系型数据库 (PostgreSQL) 存储结构化基础数据 (Fact Tables)。
4.  **服务层 (Service Layer)**: 数据集市 (Data Mart)，通过 SQL Views 封装复杂的分析逻辑（如 DORA, 战略矩阵, Jenkins 构建分析），直接对接 BI。

```mermaid
graph TD
    subgraph Data Sources
        GL[GitLab API]
        SQ[SonarQube API]
        JK[Jenkins API]
    end

    subgraph DevOps Collector
        subgraph Plugins
            P_GL[GitLab Plugin]
            P_SQ[SonarQube Plugin]
            P_JK[Jenkins Plugin]
        end
        
        subgraph Core Logic
            RMQ[RabbitMQ<br>(Task Queue)]
            IM[Identity Matcher<br>(身份归一化)]
            OM[Organization Manager<br>(组织管理)]
            DB_S[DB Session Manager]
        end
    end

    subgraph Storage & Analytics
        DB[(PostgreSQL)]
        DM[Analytics Views<br>(Data Mart)]
    end

    subgraph Consumers
        BI[BI Dashboard]
        API[Admin API]
    end

    GL --> P_GL
    SQ --> P_SQ
    JK --> P_JK
    
    P_GL --> RMQ
    P_SQ --> RMQ
    P_JK --> RMQ
    
    RMQ --> IM
    IM --> OM
    OM --> DB_S
    DB_S --> DB
    
    DB --> DM
    DM --> BI
    DM --> API
```

## 2. 核心设计理念 (Core Concepts)

### 2.1 统一身份认证 (Unified Identity)
为了解决工具间账号不互通的问题（例如 GitLab 用户名为 `zhangsan`，SonarQube 为 `zs001`），系统引入了 `users` 全局用户表。
*   **机制**: 优先基于 **Email** 进行匹配。
*   **虚拟用户**: 对于外部贡献者（无公司邮箱），标记 `is_virtual=True`，允许手动维护。

### 2.2 插件化架构 (Plugin Architecture)
每个数据源作为一个独立的 Plugin 存在，必须实现标准接口：
*   `collect_projects()`: 发现项目。
*   `sync_data()`: 执行同步逻辑。

### 2.3 分析逻辑下沉 (Analytics in Database)
我们采用 "ELT" 而非传统的 "ETL" 思维处理复杂指标。
*   **Python 代码** 仅负责将原始数据原样搬运到数据库 (Load)。
*   **SQL Views** 负责所有的业务逻辑计算（如“计算 DORA 指标”、“识别僵尸项目”）。
*   **优势**: 修改指标定义无需重新部署代码，且利用数据库引擎聚合性能更高。

## 3. 数据流设计 (Data Flow)

### 3.1 初始化阶段 (Discovery)
1.  运行 `init_discovery.py`。
2.  遍历 GitLab 顶层 Group，构建 `organizations` 树。
3.  扫描所有 Project，写入 `projects` 表（仅元数据）。

### 3.2 增量同步阶段 (Incremental Sync)
1.  **GitLab 采集 (流式 & 分批)**:
    *   **流式拉取**: 利用 Python Generator 逐页获取数据。
    *   **分批处理**: 每 500 条记录构建 Batch。
    *   **幂等写入**: Upsert 策略，支持随时断点续传。
2.  **SonarQube 采集**:
    *   关联 GitLab 项目，拉取 Quality Gate 与 Metrics。
3.  **Jenkins 采集**:
    *   同步 Job 列表，抓取 Build 详细记录（时长、结果、触发者）。

## 4. 关键技术决策 (Key Decisions)

*   **为什么全用 SQL View 做报表？**
    *   **性能**: 对于数百万级 Commits 的聚合，数据库（尤其是 PG）比 Python Pandas 更高效，且无需数据搬运。
    *   **开放性**: 任何该支持 SQL 的 BI 工具 (Superset, Tableau, PowerBI) 都可直接接入，无需开发 API。
    *   **一致性**: SQL 脚本即文档，指标定义清晰可见 (Single Source of Truth)。

*   **为什么使用 RabbitMQ？**
    *   **削峰填谷**: 应对突发的大规模同步请求。
    *   **解耦**: 调度层 (Scheduler) 与执行层 (Worker) 分离，支持多机器部署 Worker 提升并发性能。
    *   **可靠性**: 任务失败可自动重回队列，确保每一条数据都不丢失。

*   **大批量数据适配**
    *   **Generator Stream**: 内存占用 O(1)。
    *   **Batch Commit**: 兼顾写入性能与事务安全。

## 5. 扩展性设计 (Extensibility)
如需添加新指标（如“代码注释率”）：
1.  **Schema**: 修改 `models/` 增加字段。
2.  **Collector**: 修改 Plugin 填充字段。
3.  **Analytics**: 修改 `sql/PROJECT_OVERVIEW.sql` 视图定义即可生效。

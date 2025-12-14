# 系统架构设计文档 (System Architecture Design)

## 1. 架构概览 (Architecture Overview)

DevOps Data Collector 采用模块化的**ETL (Extract, Transform, Load)** 架构，旨在实现高扩展性、高可靠性和数据的一致性。

系统由三层组成：
1.  **采集层 (Collection Layer)**: 插件化适配器，负责对接不同 API (GitLab, SonarQube)。
2.  **核心层 (Core Layer)**: 负责数据清洗、实体关联、身份归一化和持久化。
3.  **存储层 (Storage Layer)**: 关系型数据库 (PostgreSQL) 存储结构化数据。

```mermaid
graph TD
    subgraph Data Sources
        GL[GitLab API]
        SQ[SonarQube API]
    end

    subgraph DevOps Collector
        subgraph Plugins
            P_GL[GitLab Plugin]
            P_SQ[SonarQube Plugin]
        end
        
        subgraph Core Logic
            IM[Identity Matcher<br>(身份归一化)]
            OM[Organization Manager<br>(组织管理)]
            DB_S[DB Session Manager]
        end
    end

    subgraph Storage
        DB[(PostgreSQL)]
    end

    GL --> P_GL
    SQ --> P_SQ
    
    P_GL --> IM
    P_SQ --> IM
    
    IM --> OM
    OM --> DB_S
    DB_S --> DB
```

## 2. 核心设计理念 (Core Concepts)

### 2.1 统一身份认证 (Unified Identity)

为了解决工具间账号不互通的问题（例如 GitLab 用户名为 `zhangsan`，SonarQube 为 `zs001`），系统引入了 `users` 全局用户表。

*   **机制**: 优先基于 **Email** 进行匹配。
*   **策略**:
    *   当采集到用户数据时，首先在 `users` 表查找是否存在相同 Email。
    *   如果存在，关联该 ID。
    *   如果不存在，创建新用户记录。
*   **虚拟用户**: 对于外部贡献者（无公司邮箱），标记 `is_virtual=True`，允许手动维护。

### 2.2 插件化架构 (Plugin Architecture)

每个数据源作为一个独立的 Plugin 存在，必须实现标准接口：
*   `collect_projects()`: 发现项目。
*   `sync_data()`: 执行同步逻辑。

这使得未来扩展 Jenkins, Jira 等新数据源时，无需修改核心代码。

### 2.3 组织架构透视 (Hierarchy Mapping)

系统不简单地平铺项目，而是将其挂载到组织树上。
*   **来源**: 从 GitLab 的 Group/Subgroup 结构或 Description 字段解析部门信息。
*   **映射**: 将解析出的部门名称映射到 `organizations` 表的层级节点。
*   **价值**: 使得“查询某个部门的代码提交量”成为可能，而非仅关注单个项目。

## 3. 数据流设计 (Data Flow)

### 3.1 初始化阶段 (Discovery)
1.  运行 `init_discovery.py`。
2.  遍历 GitLab 顶层 Group，构建 `organizations` 树。
3.  扫描所有 Project，写入 `projects` 表（仅元数据）。

### 3.2 增量同步阶段 (Incremental Sync)
1.  **GitLab 采集 (流式 & 分批)**:
    *   **流式拉取**: 利用 Python Generator 逐页获取数据，避免 huge list 加载导致内存溢出 (OOM)。
    *   **分批处理**: 每 500 条记录构建一个 Batch 并在内存中进行预处理（如身份匹配、Diff 分析）。
    *   **幂等写入**: 使用 `batch save` 策略，通过 ID 预检过滤已存在记录，实现 `Upsert` 效果。即使中间中断，再次运行也能安全补全数据。
    *   **状态更新**: 全部完成后更新项目 `sync_status` 和 `last_synced_at`。
2.  **SonarQube 采集**:
    *   遍历数据库中已存在的 Project。
    *   根据规则（如 `project.path_with_namespace`）推断 SonarQube Project Key。
    *   拉取质量指标存入 `sonar_measures`。

## 4. 关键技术决策 (Key Decisions)

*   **为什么用 SQLAlchemy ORM？**
    *   屏蔽数据库差异 (PG/MySQL/SQLite)。
    *   方便处理复杂的表关联 (Foreign Keys)。
*   **为什么不用 Celery？**
    *   保持部署简单。目前的脚本模式配合 Crontab/Jenkins 调度已足够满足 T+1 或小时级同步需求，避免引入 Redis/Broker 的运维复杂度。
*   **大批量数据适配 (Bulk Data Adaptation)**
    *   **场景**: 面对企业级 Mono-repo (如 10万+ Commits) 或首次全量归档。
    *   **策略**: 彻底摒弃全量加载。
        *   **Generator Stream**: 客户端层采用 `yield` 生成器模式，使得内存占用与数据总量无关 (O(1))。
        *   **Batch Commit**: Worker 层每 accumulation 500 条记录提交一次事务，防止长事务锁表，同时兼顾写入性能。
        *   **Idempotency**: 写入逻辑内置查重，支持随时中断、随时重跑 (Re-runnable)。

## 5. 扩展性设计 (Extensibility)

如需添加新字段（例如统计“代码注释率”）：
1.  修改 `models/` 下的 Python 类定义。
2.  利用 Alembic (后续计划引入) 或手动 ALTER TABLE 升级数据库。
3.  在 Plugin 中补充解析逻辑。

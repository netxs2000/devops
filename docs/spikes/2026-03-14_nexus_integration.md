---
status: Proposed (Active)
date: 2026-03-14
author: AI Architect
topic: Nexus 3.x OSS Artifact Traceability & FinOps Strategy
---

# Spike: Nexus 3.x OSS 元数据同步与 DORA/FinOps 深度集成方案 (已落地版)

## 1. 业务目标：让 Nexus 制品“会说话”
目前的 Nexus 仅仅是一个存储 JAR 包的“大仓库”。我们的目标是通过本次集成，实现两个核心能力：
1. **防伪溯源 (Traceability)**：通过“滴血认亲”技术，让每一个 JAR 包都能自动说出它是从哪个 **Git Commit** 生成的。
2. **孤儿清理 (FinOps)**：自动揪出那些“没人领、没人用、又占地方”的**野包**，量化存储成本。

---

## 2. 核心架构设计 (针对小白的白话解说)

### A. 数据采集“隔离网” (Worker 层)
*   **针对问题**：Nexus 里的 Snapshots (快照包) 极其庞大且杂乱。
*   **逻辑落地**：我们在 `NexusWorker` 内部安装了一个“时间过滤器”。系统会自动忽略所有 **2024-01-01** 之前的老旧资产，确保数据库里只存最有价值的近期数据。

### B. 资产血缘“滴血认亲” (Traceability Mechanism)
*   **针对问题**：JAR 包本身是一块“板砖”，看不出它是哪行代码变成的。
*   **黑科技方案**：**旁路印章文件**。
    *   我们在 CI 中推包时，顺便带一个极小的 `.properties` 文件（类似于出厂合格证）。
    *   `NexusWorker` 具备了“阅读”能力，它会自动寻找并打开这个文件，读出 `commit_sha`，然后像钉子一样，把 **Nexus 制品** 和 **GitLab 代码** 钉死在一起。
*   **代码现状**：`NexusClient` 已具备下载能力，`NexusWorker` 已具备解析逻辑，等待 CI 侧“盖章”上报。

### C. “孤儿猎手”探测大盘 (dbt 建模层)
*   **针对问题**：`nexus_component_map.csv` 登记不及时，没法知道这些包是谁的。
*   **逻辑落地**：
    1.  **自动对齐**：通过 dbt 模型 `stg_nexus_components` 每日扫描仓库。
    2.  **暴力排查**：将扫描结果与人工登记表做 `LEFT JOIN`。
    3.  **结果**：凡是没登记且超过 90 天没下载过的包，都会列入 `fct_nexus_orphan_assets` (孤儿资产事实表)，并标记为“高危幽灵”，直接推给对应的产品负责人去认领或清理。

---

## 3. 落地路线图 (Roadmap)

### 第一阶段：点亮底层大盘 (已完成 ✅)
- [x] 开发 `NexusWorker` 基础爬虫。
- [x] 建立 `2024-01-01` 增量采集隔离网。
- [x] 补齐 dbt Staging 层与 `sources.yml` 映射。
- [x] 实现 `fct_nexus_orphan_assets` 孤儿发现模型。

### 第二阶段：防伪印章对接 (执行中 🏗️)
- [x] **平台端就绪**：`NexusWorker` 现已支持解析 `devops-trace.properties` 旁路文件。
- [ ] **流水线侧改造**：与运维团队研讨，在 Jenkins/GitLab CI 的 `deploy` 阶段追加 3 行 `echo` 脚本。

### 第三阶段：财务量化与自动清理 (规划中 📅)
- [ ] **FinOps 板报**：根据文件字节大小，生成每月存储成本排行。
- [ ] **清理自动化**：对接 Nexus API 删除接口，针对“幽灵包”执行自动化硬删除清理。

---

## 4. 技术术语解释 (GLOSSARY)
*   **Component (组件)**：可以理解为一个大项目（如 `portal-api`）。
*   **Asset (资产)**：组件里的具体文件（如 `portal-api-1.0.jar` 或 `sha1` 校验文件）。
*   **Orphan (孤儿包)**：在系统里占着空间，但在我们的产品映射表里查不到主人的制品。
*   **DORA 前置时间**：从程序员按下 `Commit` 到 Nexus 产生出对应的 `JAR` 包所需的分钟数。

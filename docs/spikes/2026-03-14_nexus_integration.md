---
status: Completed & Handover (✅)
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
- [x] **[DB-01] 物理字段扩展**：已增加 `commit_sha` 物理列。 (2026-03-14)
- [x] **[DB-02] 索引优化**：已建立 `ix_nexus_components_lookup` 联合索引。 (2026-03-14)

### 第二阶段：防伪印章对接 (执行中 🏗️)
- [x] **平台端就绪**：`NexusWorker` 已支持解析旁路文件。
- [x] **[dbt-03/04] DORA 链路贯通**：已实现 `int_nexus_commits` 与 `fct_dora_metrics` 关联，支持打包延迟度量。 (2026-03-14)
- [ ] **流水线侧改造**：与运维团队研讨，在 Jenkins/GitLab CI 的 `deploy` 阶段追加 3 行 `echo` 脚本。

### 第三阶段：财务量化与自动清理 (已交付 ✅)
- [x] **[dbt-05] 费率折算与成本事实表**：已建立 `fct_nexus_storage_costs` 模型。
- [x] **FinOps 板报**：已通过 Streamlit 建立 `20_Nexus_FinOps.py` 展示大屏。 (2026-03-14)
- [x] **[Script-06] 清理逻辑打分系统**：已实现 `fct_nexus_cleanup_list` 积分制名单。 (2026-03-14)
- [ ] **清理自动化 (待授权)**：对接 Nexus API 删除接口，针对“高危包”执行自动化硬删除清理。 (需运维配合)

---

## 4. 后续详细执行清单 (Implementation Tasks)
为了完成上述路线图，建议按以下颗粒度任务进行实施，请 USER 决策开启顺序：

### 任务域 1：基础架构加固 (后勤准备)
- [x] **[DB-01] 物理字段扩展**：在 `nexus_components` 表中正式增加 `commit_sha (String)` 字段。 (2026-03-14 完成)
- [x] **[DB-02] 索引优化**：为 `repository`, `group`, `name` 增加联合索引。 (2026-03-14 完成)

### 任务域 2：DORA 链路贯通 (核心价值)
- [x] **[dbt-03] 建立“代码-制品”映射模型**：编写 `int_nexus_commits.sql`。 (2026-03-14 完成)
- [x] **[dbt-04] 产出 DORA 核心事实表**：更新 `fct_dora_metrics`，将 Nexus 产出作为交付流水线的“终点站”时间。 (2026-03-14 完成)

### 任务域 3：FinOps 财务量化 (成本控制)
- [x] **[dbt-05] 接入费率折算**：编写 `marts_nexus_storage_costs.sql` 以及配套的 `seed_nexus_storage_rates.csv`。 (2026-03-14 完成)
- [x] **[Streamlit] 搭建“成本黑洞”排行榜**：已完成 `20_Nexus_FinOps.py` 页面。 (2026-03-14 完成)

### 任务域 4：自动化治理 (逻辑已贯通)
- [x] **[Script-06] 清理逻辑打分系统**：已在 dbt 中实现 `is_safe_to_auto_cleanup` 标识。 (2026-03-14 完成)
- [ ] **[Nexus-API] 开发清理执行脚本**：需要 Nexus 管理员 Token 后执行物理删除封装。

---

## 5. 技术术语解释 (GLOSSARY)
*   **Component (组件)**：可以理解为一个大项目（如 `portal-api`）。
*   **Asset (资产)**：组件里的具体文件（如 `portal-api-1.0.jar` 或 `sha1` 校验文件）。
*   **Orphan (孤儿包)**：在系统里占着空间，但在我们的产品映射表里查不到主人的制品。
*   **DORA 前置时间**：从程序员按下 `Commit` 到 Nexus 产生出对应的 `JAR` 包所需的分钟数。


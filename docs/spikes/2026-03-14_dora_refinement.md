---
status: Proposed (Active)
date: 2026-03-14
author: AI Architect
topic: DORA 2.0 Refinement - End-to-End Metrics with ZenTao & GitLab
---

# Spike: DORA 2.0 效能精修方案 — 全通路贯通与事故精准画像

## 1. 业务目标：从“技术指标”走向“业务指标”
当前的 DORA 指标仅观测了 GitLab 内部的代码活动。DORA 2.0 的目标是利用**禅道 (ZenTao)** 作为业务终点，实现：
1. **真实部署频率**：以禅道“发布记录”为准，过滤掉无效的自动化流水线跑分。
2. **端到端前置时间**：追踪“需求提出 -> 代码提交 -> 制品产出 -> 业务发布”的全链路时间。
3. **真实事故回溯**：精准锁定 P1 级且标记为“生产环境”的 Bug，自动计算 MTTR。

---

## 2. 逻辑蓝图 (小白解说版)

### A. 关联“接头暗号” (Commit to Issue)
*   **规则**：通过正则解析 GitLab 提交信息中的 `#123`。
*   **逻辑**：如果一个提交说 `fix: #123 性能优化`，我们就在数据库里把代码和禅道 123 号需求“缝”在一起。

### B. 部署频率“代理人” (Deployment Proxy)
*   **规则**：使用 `zentao_releases` 表。
*   **逻辑**：只有在禅道里点下了“发布”按钮的记录，才算作一次 DORA 部署。

### C. 线上事故“雷达” (Incident Identification)
*   **规则**：
    1. 类型是 `Bug`。
    2. 优先级是 `P1` (严重)。
    3. 特殊标记：`browser` (浏览器) 字段记录为 **“生产环境(单选)”**。
*   **目的**：自动滤除测试阶段的普通缺陷，只保留影响客户的重大事故。

---

## 3. 技术实施路线图 (Implementation Roadmap)

### 第一阶段：数据颗粒度升级 (Staging) (已完成 ✅)
- [x] **[dbt-STG-01]** 改造 `stg_zentao_issues`：解析 `raw_data` 中的 `browser` 字段定义为 `found_in_environment`。 (2026-03-14)
- [x] **[dbt-STG-02]** 改造 `stg_gitlab_commits`：提取 `Issue_ID` (zentao_id) 辅助列。 (2026-03-14)
- [x] **[dbt-STG-03]** 补齐 `stg_zentao_builds` 基础模型。 (2026-03-14)

### 第二阶段：全链路缝合 (Intermediate) (已完成 ✅)
- [x] **[dbt-INT-01]** 编写 `int_dora_issue_commit_lifecycle`：计算“需求到代码”的响应与开发耗时。 (2026-03-14)
- [x] **[dbt-INT-02]** 编写 `int_dora_production_incidents`：锁定 P1 级生产事故。 (2026-03-14)

### 第三阶段：DORA 看板 2.0 (Marts) (执行中 🏗️)
- [x] **[dbt-FCT-05]** 建立 `fct_dora_metrics_v2` 精修事实表：引入 Release 频率与生产事故 MTTR。 (2026-03-14)
- [ ] **[Streamlit]** 绘制“交付漏斗图”与“瓶颈雷达图”。 (待开启)

---

## 4. 风险与不确定性
- **规范执行**：如果程序员忘了写 `#ID`，数据会出现断链（漏统计）。我们需要通过监控平台找出这些“无名 Commit”。
- **时间语义**：禅道 Release 的 `date` 字段是否代表真实上线时刻，需在模型中留出 2 小时时差冗余。

---

## 5. [小白专区] 预期效果预览
完成此方案后，您不仅会看到 DORA 分数，还会看到更具人性化的分析：
> **“本月‘交付频率’有所下降，通过瓶颈分析发现，是因为‘制品产出 -> 业务发布’中间滞留了 3 天之久，建议关注运维发布的审批流程。”**

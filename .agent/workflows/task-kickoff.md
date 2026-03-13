---
description: 任务启动仪式 — 含分级判定 + Task Brief 模板 + 风险预判
---

# 任务启动仪式 (Task Kickoff Ceremony)

> **触发时机**：每当接收到新任务时，Agent 必须在编码前完成本流程。
> **核心目标**：30 秒内完成任务定级，并根据级别路由到对应的 SOP。

---

## Step 1: 任务分级判定 (Task Classification)

按以下决策树快速定级：

```
收到新任务
├── 是否涉及「探索/评估/可行性验证」？
│   └── Yes → 🔵 Spike (S) → 执行 /spike 流程
├── 是否涉及「新基础设施/消息拓扑/核心模型重构」？
│   └── Yes → 🔴 L4 (架构级)
├── 是否跨越 2 个以上模块 或 涉及 DB Schema 变更？
│   └── Yes → 🟠 L3 (复杂)
├── 改动范围 > 3 个文件 或 需要新建文件？
│   └── Yes → 🟡 L2 (标准)
└── 否则 → 🟢 L1 (快修)
```

**输出格式**：在回复中声明 `[Task Level: Lx]`，锁定后续流程路线。

---

## Step 2: Task Brief (按级别差异化)

### 🟢 L1 — 免 Brief
- 无需产出 Task Brief。直接在 Commit Message 中描述改了什么和为什么。

### 🟡 L2 — Lite Brief (3 行)
在回复中以文本形式确认：
```
🎯 目标：[一句话描述要解决的问题]
🔲 边界：[不做什么 / 排除范围]
✅ 验收：[什么状态算完成]
```

### 🟠 L3 — Full Brief (含风险)
```
🎯 目标：[问题描述 + 期望结果]
🔲 边界：[不做什么 / 排除范围 / 对外部系统的假设]
⏱️ 估时：[预估工时，含拆解依据]
⚠️ 风险：[已知风险，关联 lessons-learned.log 中的历史教训]
✅ 验收：[可量化的验收标准，含测试覆盖要求]
📦 切片：[拆分为哪几个垂直交付切片]
```

### 🔴 L4 — RFC 门控
- 必须先产出 RFC 文档（存入 `docs/design/`），经用户评审通过后，方可填写 Full Brief。
- RFC 模板参见 `contexts.md` 14.2 章。

---

## Step 3: 风险预判 (Risk Pre-check) — L2 及以上

Agent 必须扫描 `docs/lessons-learned.log`，自动关联与本次任务相关的历史教训：

1. 按 Domain 关键字匹配（如任务涉及 ZenTao → 检索 `ZenTao/*` 域的所有记录）。
2. 若有匹配：在 Brief 的 ⚠️ 风险 部分列出关联教训编号和防御规则。
3. 若无匹配：显式声明 `[Risk Check]: 未发现历史关联风险`。

---

## Step 4: 估时与时间盒 (Estimation & Timebox) — L2 及以上

| 级别 | 估时要求 | 超时检查点 |
| :---: | :--- | :--- |
| L2 | 粗粒度估时（0.5h / 1h / 2h / 4h / 1d / 2d） | 超过估时 50% 时主动暂停并汇报 |
| L3 | 按切片估时，总计不超过 5 天 | 每个切片完成时做 Mini-Demo |
| L4 | RFC 阶段估算，实施阶段按子任务估时 | 每日更新 `progress.txt` |
| S | 强制 Timebox ≤ 4h | 到期必须出结论 |

**超时协议**：当实际耗时超过估时的 150% 时，Agent 必须立即暂停并发起反向交互：
> "⏰ 超时预警：预估 [Xh]，已耗时 [Yh]。阻塞原因：[...]。建议：[A] 继续 / [B] 调整范围 / [C] 转为 Spike 重新评估"

---

## Step 5: 流程路由矩阵 (SOP Routing)

确认级别后，按以下矩阵执行对应步骤：

| 步骤 | L1 | L2 | L3 | L4 | S |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 前置采访 | ❌ | ✅ 快速版 | ✅ 完整版 | ✅ 完整版 | ❌ |
| Task Brief | ❌ | Lite | Full | RFC+Full | ❌ |
| 风险预判 | ❌ | ✅ | ✅ | ✅ | ❌ |
| 分支策略 | main 直推 | Feature Branch | Feature Branch | Feature Branch | 临时分支/tmp |
| 估时 | ❌ | ✅ | ✅ | ✅ | Timebox |
| 阶段验收 | ❌ | ❌ | ✅ Mini-Demo | ✅ Per Sub-task | Go/No-Go |
| 回滚预案 | ❌ | 条件触发 | ✅ | ✅ | ❌ |
| `/code-review` | 自审 | ✅ | ✅ 每切片 | ✅ 每切片 | ❌ |
| `/lint` | ✅ | ✅ | ✅ | ✅ | ❌ |
| 测试 | Unit | Unit+Int | Unit+Int+容器 | Full+E2E | POC 级 |
| `/doc-update` | progress 仅 | ✅ | ✅ | ✅ 全量 | 结论归档 |
| `/merge` | 直推 | ✅ | ✅ | ✅ | ❌ |
| Lesson Learned | 条件 | 条件 | ✅ 强制 | ✅ 强制 | 结论报告 |

---

## 完工签章

Task Brief 确认后，Agent 回复中必须包含：
```
[Kickoff Complete] Level: Lx | ETA: Xh | Branch: feat/xxx | Risks: N identified
```

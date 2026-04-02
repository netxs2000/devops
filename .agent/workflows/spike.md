---
description: Spike 技术探针流程 — 时间盒约束 + Go/No-Go 结论报告
---

# Spike 探针工作流 (Spike / Technical Investigation)

> **适用场景**：技术可行性验证、新库评估、性能基准测试、架构方案 POC。
> **核心约束**：Spike 代码严禁直接合入主线，必须重写为正式实现。

---

## Step 1: 定义探针目标 (Define the Question)

在回复中明确以下三要素：

```
🔬 探针问题：[用一个可回答 Yes/No 的问题描述，如 "dbt-expectations 能否完全替代 Great Expectations？"]
📏 成功标准：[什么证据能回答这个问题，如 "核心 5 条测试规则可迁移 + 执行时间 < 2min"]
⏱️ 时间盒：[默认 4h，最长 8h，超过需拆分]
```

---

## Step 2: 创建隔离环境 (Isolation)

- **代码存放**：实验代码放在 `/tmp/spike_<topic>/` 或独立分支 `spike/<topic>`。
- **严禁污染**：不修改 `main` 分支的任何生产代码。
- **依赖隔离**：若需安装新库，在虚拟环境或容器内操作，不修改 `requirements.txt`。

---

## Step 3: 快速实验 (Experiment)

- 以最小代码量验证核心假设。
- 每 1 小时做一次内部 Checkpoint：当前进度如何？是否需要调整方向？
- **严禁完美主义**：Spike 的目标是回答问题，不是交付产品级代码。

---

## Step 4: 结论报告 (Conclusion Report)

时间盒到期时（无论成功与否），必须产出以下结构化报告：

```markdown
## Spike 结论报告: <主题> [MANDATORY TAG: [Spike-Result]]

- **日期**: YYYY-MM-DD
- **耗时**: Xh / 时间盒 Yh
- **结论**: 🟢 Go / 🔴 No-Go / 🟡 Need More Investigation

### 发现 (Findings)
1. [关键发现 1]
2. [关键发现 2]

### 证据 (Evidence)
- [测试结果 / 基准数据 / 截图]

### 风险与限制 (Risks & Limitations)
- [已发现的风险或限制条件]

### 下一步 (Next Steps)
- 🟢 Go: 转为 [L2/L3] 正式任务，预估 [Xd]
- 🔴 No-Go: 原因 [...]，替代方案 [...]
- 🟡 Need More: 需要额外 [Xh] 验证 [具体问题]
```

**报告归档**：存入 `docs/spikes/YYYY-MM-DD_<topic>.md`。

---

## Step 5: 清理 (Cleanup)

// turbo
1. 删除 `/tmp/spike_<topic>/` 下的实验代码。
2. 若使用了独立分支，确认不合入后删除。
3. **环境复核**：若实验涉及修改 `.env` 或安装系统包，必须还原至 `git checkout` 状态。
4. 确认 `git status` 无残留。

---

## 关键红线

- ❌ **严禁**在 Spike 过程中修改生产代码
- ❌ **严禁**将 Spike 代码直接 merge 到 main（必须重写）
- ❌ **严禁**超时不出结论（即使结论是 "Need More"）
- ❌ **严禁**在 Spike 过程中演变为“深挖 Bug 修复”，若遇到阻塞应立即宣告 No-Go 而非纠缠。
- ✅ **必须**产出结论报告并记录于 `docs/session-history.log`，无论结果如何

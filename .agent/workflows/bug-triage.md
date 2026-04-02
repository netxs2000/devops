---
description: [bug-triage] 故障排查与修复工作流 — 强制 TDD 模式与日志溯源归因
---

# 故障排查与修复工作流 (Bug Triage & Fix Workflow)

> **触发时机**：处理 L1/L2 级别的线上缺陷、测试用例失败或异常行为修复。
> **核心策略**：复现 (Reproduce) -> 归因 (Attribution) -> 隔离修复 (Isolated Fix)。

---

## Step 1: 缺陷复现 (Reproduction - MANDATORY)

在提出修复代码前，AI **必须**首先通过编码实现缺陷复现：
1. **编写“自毁测试 (Self-Destructing Test)”**：在 `tests/debug/` 下创建一个临时的 `test_fail.py`，模拟导致 Bug 的输入。
2. **运行并确认失败**：必须输出 `AssertionError` 或期望的异常。
3. **输出逻辑**：汇报 `[Reproduction]: 失败用例已复现，报错原因为 xxx`。

## Step 2: 深度归因与日志溯源 (Attribution)

1. **查阅日志**：分析 `devops_collector` 容器日志或 Traceback。
2. **定位三界**：
   - **数据源问题** (Source): 上游 API 接口非标或 Token 过期？
   - **核心逻辑问题** (Service): 业务公式计算错误或空指针？
   - **持久层问题** (Persistence): 数据库并发死锁或类型溢出？
3. **经验对齐**：检索 `docs/lessons-learned.log` 是否有同类报错（如：ZenTao 401 认证死循环）。

## Step 3: 隔离修复与 TDD (The Fix)

1. **最小化修改**：仅针对 Step 1 失败的切片进行修复。
2. **绿色验证 (Green Build)**：运行 Step 1 中创建的测试，确认其现在通过。
3. **回归测试**：运行受影响模块的全量插件测试 `pytest tests/plugins/<domain>/`。

## Step 4: 知识沉淀 (Lessons Learned)

每当修复一个“隐蔽”或“反复出现”的 Bug，必须按照 [`AGENTS.md`](AGENTS.md) 的规定同步：
- 更新 `docs/lessons-learned.log` 记录问题的 Universal Rule（如：严禁在循环中执行 `db.commit()`）。

---

## 完工签章

在回复中包含：
```
[Bug Fixed] Root Cause: [Domain/Logic] | Evidence: Passed test_fail.py | Lesson Learned: Updated
```

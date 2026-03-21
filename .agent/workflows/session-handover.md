---
description: 会话交接协议 — 上下文恢复清单与状态对齐
---

# 会话交接协议 (Session Handover Protocol)

> **适用场景**：新会话开始时、会话中断后恢复时。
> **核心目标**：确保新会话在 60 秒内与上一次会话的状态完全对齐，避免重复探索或遗漏中间状态。

---

## Part A: 新会话启动清单 (Session Bootstrap Checklist)

Agent 在每次新会话开始时，必须按以下顺序执行上下文恢复：

### 1. 读取项目状态快照 (30s)
// turbo
```powershell
# 读取进展跟踪
cat progress.txt
```

// turbo
```powershell
# 确认当前 Git 状态（分支 + 未提交变更）
git branch --show-current
git status --short
```

// turbo
```powershell
# 确认容器运行状态
docker-compose ps --format "table {{.Name}}\t{{.Status}}"
```

### 2. 扫描最近教训 (15s)
// turbo
```powershell
# 读取最近 10 条 Lessons Learned
Get-Content docs/lessons-learned.log | Select-Object -Last 15
```

### 3. 识别未完成工作 (15s)
- 检查 `progress.txt` 的 [进行中] 区域
- 检查 `git stash list` 是否有暂存的工作
- 检查是否有未合并的 Feature Branch

### 4. 产出状态摘要
完成以上步骤后，Agent 必须向用户呈现一份简洁的状态摘要：

```
📍 会话恢复摘要:
- 分支: main | feat/xxx
- 未提交变更: X files modified
- 容器状态: ✅ All healthy / ⚠️ [service] unhealthy
- 当前焦点: [从 progress.txt 提取]
- 待办优先: [从 progress.txt 提取前 2 项]
- 近期教训: [最近 3 条高相关的 Lesson]
```

---

## Part B: 会话结束交接 (Session Debriefing)

每次会话结束前（或用户明确表示切换话题/结束工作时），Agent 应主动执行：

### 1. 状态持久化
- 更新 `progress.txt`（将已完成的移到「最近完成」，新发现的加入「接下来」）
- 确保所有有价值的中间状态已 Commit 或 Stash

### 2. 🚨 知识割取 Harvest [MANDATORY — 不得跳过]
> **触发判断**：本次会话中是否有任何问题经历了 **2 次以上尝试才解决**？或发现了数据源/工具链的**非标行为**？
> **回答 YES → 必须立即执行，不得以 Token 不足为由推迟。**

自问清单（逐条过）：
- [ ] 有没有 Mock/测试工具与 ORM 不兼容的坑？
- [ ] 有没有 Schema/FK 类型不匹配导致的错误？
- [ ] 有没有正则/解析逻辑的边界 bug？
- [ ] 有没有断言边界值（时序、数值精度）的失效？
- [ ] 有没有 Pydantic / SQLAlchemy 版本行为的差异？

对每一个 YES 项，在 `docs/lessons-learned.log` 末尾追加一行，格式：
```
| {date} | {Domain} | {现象} | {根因} | {防线规则} |
```

### 3. 交接备忘 (Handover Notes)
在 `progress.txt` 的 [当前状态] 区域，留下给下一个 Agent/会话的简要说明：
- 当前卡在哪里？
- 下一步最该做什么？
- 有什么已经尝试过但失败的方案？（避免重复探索）

### 4. 环境卫生
// turbo
```powershell
# 清理临时文件
make clean
```

---

## Part C: 中断恢复 (Crash Recovery)

当会话因意外中断（如网络断开、Token 超时）后恢复时：

1. **严禁假设上一次操作成功**。必须通过工具验证：
   - `git log -1` 确认最后一次提交内容
   - `docker-compose ps` 确认服务状态
   - `git diff --stat` 确认未提交的变更
2. **检查一致性**：`progress.txt` 中记录的状态是否与物理事实一致。
3. **若发现不一致**：以物理事实为准，修正 `progress.txt`。

---

## 关键原则

- **Physical Truth > Logical Consistency**：永远以工具输出为准，不靠推理猜测
- **Zero Assumption**：不假设上次会话做了什么，每次都验证
- **Fail-Safe**：宁可多读一个文件，也不要跳过验证步骤

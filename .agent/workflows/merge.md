---
description: 分支合并到 main 的完整检查流程 (Pre-merge Checklist)
---

# Pre-merge Checklist Workflow

> 参考原则定义：`contexts.md` 第 13 章 "合并前检查清单"。
> 任一 🔴 BLOCK 步骤 FAIL 即中止合并，修复后重新执行。

## 前置条件

- 当前处于待合并的功能分支上 (如 `feat/xxx`)
- 所有功能开发已完成，代码已 commit

---

## Step 1: Rebase 同步 🔴 BLOCK

确保功能分支基于最新的 main，并保持线性历史。

```bash
git fetch origin
git rebase origin/main
```

- 若有冲突，手动解决后 `git rebase --continue`
- 验证：`git log --oneline -5` 确认历史线性，无 merge commit

// turbo
## Step 2: 终极验证防御 (Total Verification Defense) 🔴 BLOCK

按照 `AGENTS.md` 的“终极验证律”，在合入前必须执行全量校验：

```bash
make verify
```

- **通过条件**：
    - [ ] `make lint` 0 错误。
    - [ ] `make check-imports` 0 冲突。
    - [ ] 全量 `pytest` PASSED。
    - [ ] **硬性指标**：代码覆盖率 (Coverage) >= **80%**。
- **取证要求**：在此步骤完成时，必须在工作记录中粘贴 `make verify` 的关键输出文本，以证明物理通过。
- **降级条件**：禁止降级。若环境不支，必须在修复环境后重新执行。

## Step 5: 容器部署验证 🔴 BLOCK (可降级)

```bash
make deploy
```

- **通过条件**：所有容器启动成功，健康检查通过
- 可选追加验证（重大变更时）：
  ```bash
  make deploy-prod     # 生产模式验证
  make deploy-offline  # 离线模式验证
  ```
- **降级条件**：同 Step 4，记录阻塞原因后可有条件跳过

// turbo
## Step 6: 环境清理 (Cleanup) 🟡 WARN

清理因开发/调试/测试产生的临时文件，确保零残留。

```bash
make clean
```

手动确认：

- [ ] `git status` 无意外的 untracked 临时文件（`.log`, `.tmp`, `debug_*.py` 等）
- [ ] 无 AI 生成的中间分析文件残留在项目目录中
- [ ] 若发现 `.gitignore` 未覆盖的新类型临时文件，补充到 `.gitignore`

## Step 7: 文档同步检查 🟡 WARN

手动确认以下文档已更新：

1. **`progress.txt`**：记录本次变更内容、验证结果、遗留问题
2. **`contexts.md`**（仅当涉及以下变更时）：
   - 技术栈变更（新增/移除核心依赖）
   - 架构决策调整（新增模块、数据流变更）
   - 新增开发规范或核心模型
3. **`DATA_DICTIONARY.md`**（仅当模型变更时）：执行 `make docs` 刷新

## Step 8: 安全自检 🟡 WARN

手动确认：

- [ ] 无硬编码的 API Key、密码或 Token（应使用 `.env` 环境变量）
- [ ] 新增的第三方依赖无已知 CVE 漏洞
- [ ] 日志不打印敏感信息（token, password, key 等字段已屏蔽）

## Step 9: 数据库兼容性检查 🔴 BLOCK (仅涉及 Schema 变更时)

- [ ] Schema 变更向后兼容（不能同时修改 Schema 和依赖该 Schema 的代码）
- [ ] 遵循安全变更顺序：Add Column → Deploy Code → Drop Old Column
- [ ] 无破坏性变更（删表、删列、重命名）出现在单次合并中

---

## 执行合并

所有检查通过后，执行 Squash Merge：

```bash
# 切换到 main 分支
git checkout main
git pull origin main

# Squash Merge（将功能分支所有 commit 压缩为一个）
git merge --squash <feature-branch>

# 编写语义化的合并提交信息
# 格式: type(scope): subject
# 示例: feat(zt): 支持禅道任务与工时采集
git commit

# 推送到远程
git push origin main

# 清理功能分支
git branch -d <feature-branch>
git push origin --delete <feature-branch>
```

---

## 降级合并记录模板

当 Step 4/5 因环境问题无法执行时，在 `progress.txt` 的"进行中"区域添加：

```
- [ ] [待补验证] feat/xxx 已合入 main (YYYY-MM-DD)
    - 已通过: Rebase + Lint + 本地单元测试 (20/20 passed)
    - 未执行: make test (Docker 网络超时) / make deploy (镜像拉取失败)
    - 阻塞原因: [具体描述]
    - 补验证时间: 待环境恢复后执行
```

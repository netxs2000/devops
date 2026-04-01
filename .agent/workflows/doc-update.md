---
description: 同步更新项目相关文档 (progress.txt, contexts.md, sessions-learned.log 等)
---

# /doc-update 工作流

当任务达到重要检查点或准备提交时，执行以下步骤以确保「单一事实来源 (SSOT)」：

## 1. 自动分析变更影响 (Impact Analysis)
AI 必须回顾本次会话的所有 `replace_file_content` 和终端执行结果，识别以下影响：
- **功能变更** -> 更新 `progress.txt` [最近完成]
- **架构/规范变更** -> 更新 `contexts.md` 相应章节
- **非标行为/故障排除** -> 更新 `docs/lessons-learned.log`
- **模型/Schema 变更** -> 执行 `make docs` 更新数据字典
- **配置项增删** -> 更新 `.env.example`
- **Spike 探针完成** -> 将结论报告归档至 `docs/spikes/YYYY-MM-DD_<topic>.md`

## 2. 执行文档同步 (Synchronization)
按优先级顺序更新以下文件：
1. **[P0] `progress.txt`**：锁定当前状态。
2. **[P0] `docs/session-history.log`**：记录会话审计与交接。
3. **[P0] `docs/lessons-learned.log`**：沉淀实战经验。
4. **[P1] `contexts.md`**：固化长期规范。
5. **[P2] `CHANGELOG.md`**：记录版本演进（若适用）。

## 3. 结果验证 (Verification)
- 检查 `git status` 确保文档已修改。
- 确保文档中的链接有效。
// turbo
- 执行 `make docs` 以确保数据字典是最新的（若涉及 models 变更）。

## 4. 完工签章 (Signing Off)
在回复中包含：`[Status]: Documentation Synced`。

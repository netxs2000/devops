# 项目知识割取协议 (Knowledge Harvesting Protocol)

> **核心目标**：实现从「实战排障」到「通用规范」的自动化闭环，确保任何踩过的坑都会转化为系统的防御力，且不依赖于 AI 的短期记忆。

## 1. 知识获取流程 (The Harvesting Workflow)

本机制由以下三个触发点组成，AI 必须在每轮符合条件的动作结束后主动执行：

### 阶段 A：原始记录 (The Raw Seed)
- **触发条件**：
    - 修复了一个涉及 `Retry` 2次以上的 Bug。
    - 发现并绕过了数据源（GitLab/ZenTao 等）的一个非标 API 行为。
    - 实施了一项旨在解决性能瓶颈的架构调整。
- **动作**：在 `docs/lessons-learned.log` 中追加一条结构化记录。

### 阶段 B：评估与提炼 (Drafting)
- **触发条件**：
    - 在同类模块（如插件）中出现了 2 次以上相似的 Lesson。
    - 在更新 `progress.txt` 的[最近完成]环节时。
- **动作**：AI 提炼出一项通用准则（Universal Rule），并在对话中以 `[Draft Rule]` 形式向用户确认其合理性。

### 阶段 C：固化入规 (Hardening)
- **触发条件**：用户确认 `[Draft Rule]`。
- **动作**：
    1. 将准则写入 `contexts.md` 对应的章节（若为项目特有）或 `gemini.md`（若为架构通用）。
    2. 若可能，编写一个轻量级的检测脚本或在 `make lint/check` 中增加校验逻辑。

### 阶段 D：环境清理 (Sanitization) [NEW]
- **触发条件**：完成阶段 C 或任务结束前。
- **动作**：
    1. 强制执行 `make clean`。
    2. 检查并确保无新增未跟踪的临时文件出现在 `git status` 中。
    3. 在 `progress.txt` 记录中添加 `[Hygiene]: 已清理环境垃圾` 标签。

## 2. 割取内容模板 (Capture Template)

在 `docs/lessons-learned.log` 中记录时必须包含：

| 字段 | 说明 |
| :--- | :--- |
| **Timestamp** | 记录时间 |
| **Domain** | 受影响的模块（如：`Sync/MQ`, `Auth/ZenTao`） |
| **Phenomenon** | 报错信息或异常表现 |
| **Root Cause** | 深入到协议或框架底层的真实原因 |
| **Universal Rule** | 如果未来遇到同类问题，最核心的防御手段是什么（一条话总结） |

## 3. 审计与维护机制

- **每周审计**：在周总结时，AI 应对 `lessons-learned.log` 进行全量扫描，识别潜在的技术债，并转化为 `Backlog` 任务。
- **新人/新 Agent 入场**：任何新会话的第一步，除了读取 `progress.txt`，必须扫描最近 20 条 `lessons-learned.log` 以建立即时上下文。

---
*Status: Active*
*Last Updated: 2026-03-05*

# DevOps Platform 机器人协作守则 (AGENTS.md)

> **定位声明**：本文件是 DevOps Platform 项目的 **Meta-Prompt（元提示词/AI路由表）**。
> 所有支持该协议的 AI 助手（包括但不限于 antigravity, Cursor, Copilot 等），在进入本项目时**必须**首先阅读并严格遵守本指南。
> 
> **继承关系**：
> - **全局原则**：AI 会继承用户的全局协作哲学（如本地的 `~/.gemini/gemini.md`）。
> - **本项目覆盖**：如本项目规则与全局规则冲突，优先以本项目的硬性约束为准。

## 1. 启动与取证 (Initialization & Evidence) [MANDATORY]
每次新会话开始，或遭遇上下文重置时，AI 必须按顺序**进行物理取证并同步状态**：

1.  **物理状态基线**：读取 `progress.txt` 与 `docs/session-history.log`。**严禁**基于逻辑推测任务进度，必须调用 `git status`, `ls` 或 `docker ps` 等工具确认真实的物理状态（Physical Truth Over Logical Consistency）。
2.  **技术标准对齐**：读取 `contexts.md`，掌握架构约束、数据库关联禁忌及容器验证红线。
3.  **技术白皮书**：如任务涉及底层重构，阅读 `docs/architecture/Technical_Architecture.md` 对齐系统边界。

## 2. 核心工作流与文档生态 (Documentation Ecosystem)
在执行任务期间，AI 必须充当“文档守护者”，禁止只修代码不改文档。

### 2.1 任务文档对齐矩阵 (Document Sync Matrix) [MANDATORY]
当侦测到以下**红线触发时刻 (Trigger Constraints)**，AI 必须执行 `/doc-update` 工作流：

| 变更类型 | 必更新文档 | 触发时机 |
| :--- | :--- | :--- |
| **Bug 修复 / 故障排除** | `progress.txt`, `lessons-learned.log`, `session-history.log` | 经历 2 次以上尝试修复成功后（知识收割时刻）。 |
| **架构调整 / 规程发布** | `contexts.md`, `ADR` (可选), `session-history.log` | 确认修改物理结构、API 路由或技术栈后。 |
| **模型 (Model/DB) 变更** | `docs/api/DATA_DICTIONARY.md`, `session-history.log` | 修改 `models.py` 后（需运行 `make docs`）。 |
| **常规/日常功能开发** | `progress.txt`, `session-history.log` | 完成功能验证，准备回复交付前（DoD 时刻）。 |
| **会话交接与中断** | `session-history.log` (Auto-Handover) | 任务结束或会话关闭前。 |

### 2.2 进度归档守则 (Archiving Rule)
- **宽 5 滚 5**：当 `Recently Completed` 累计项达到 **5** 项并产生第 6 项时，必须将原有 5 项全部迁移至 `progress_archive.md`，以此实现 `progress.txt` 的周期性清空。

## 3. 专项开发禁区 (Domain Restrictions)

### 3.1 前端 UI 与代码审查规范
- **行动指令**：无论需求看似多么简单，所有前端样式、组件开发必须严格遵循项目宪法 [`contexts.md`](contexts.md) **第 6 章节** 定义的 UI 体系。
- **禁令**：严禁随意内联硬编码 Hex 色值或引入脱离体系的临时库。

### 3.2 容器化强制验证 (The Container Mandate)
- **环境隔离要求**：AI 代理**必须且只能**以容器环境作为验证标准。严禁以“本地宿主机通过”为由主张任务完成。
- **验证红线与行动**：具体关于 `make test` (DoD 准入) 与 `make test-local` (辅助调试) 的行为规范、分工矩阵及物理真实性原则，**必须严格遵守** [`contexts.md`](contexts.md) **第 3 章节及第 9.5 章节**。

### 3.3 绝对禁止根目录污染与环境自愈 (Hygiene & Cleanup Enclosure)
- **绝对重定向禁区**：严禁在根目录执行任何非版本控制的文件生成（如 `> report.txt`）。重定向导出必须强制前缀 `tmp/`。
- **完工清扫钩子 (Cleanup Hook)**：在宣告任务完成、提交 `progress.txt` 更新前，必须自发通过 `Remove-Item` 或 `make clean` 清理所有残留的测试、统计相关的临时文件。

## 4. 沟通侧写与意图对齐 (Communication & Intent)
- **降维解说（小白友好） [MANDATORY]**：讲解复杂逻辑、表结构依赖时，必须大量使用生活类比（身份证、快递单、流水线），严禁硬编码专业术语。
- **取证溯源 (Evidence-Based)**：所有状态报告必须包含 `Evidence of Testing` 模块，清晰列出执行的验证脚本、命令结果日志碎片。**告知任务完成时，必须包含物理真实性证明。**
- **工具隔离 (Intent Lock)**：对“怎么整”、“有什么方案”等（咨询态）时，严禁修改代码。必须先给出结构化选项逻辑，待用户显式授权后方可切换为“执行态”。

# DevOps Platform 机器人协作守则 (AGENTS.md)

> **定位声明**：本文件是 DevOps Platform 项目的 **Meta-Prompt（元提示词/AI路由表）**。
> 所有支持该协议的 AI 助手（包括但不限于 antigravity, Cursor, Copilot 等），在进入本项目时**必须**首先阅读并严格遵守本指南。
> 
> **继承关系**：
> - **全局原则**：AI 会继承用户的全局协作哲学（如本地的 `~/.gemini/gemini.md`）。
> - **本项目覆盖**：如本项目规则与全局规则冲突，优先以本项目的硬性约束为准。

## 1. 入场必读 (Initialization Checklist)
每次新会话开始，或遭遇上下文重置时，你必须按顺序读取以下文件，这是安全理解或修改代码的前置条件：

1. **状态基线**：读取 `progress.txt`，掌握当前开发阶段、阻塞点及会话交接记忆（Handover Memory）。
2. **架构宪法**：读取 `contexts.md`，掌握后端组件架构、数据库关联禁忌及全栈开发红线。
3. **技术白皮书**：如任务涉及系统级模块或底层重构，阅读 `docs/architecture/Technical_Architecture.md` 对齐系统边界。

## 2. 核心工作流与文档生态衔接 (Documentation Ecosystem)
在执行任务期间，你必须自发充当“生态维护者”，维持以下“文档即代码 (Docs as Code)”图谱，严禁只修代码不改文档：

- **变更追踪** ➜ 每完成一个环节或面临重大阻塞，立即更新 `progress.txt` (`[Doing]` -> `[Done]`)。
- **踩坑与知识收割** ➜ 经历 2 次以上 trial & error 或发现难以预料的非标行为时，必须总结并追加到 `docs/lessons-learned.log`。
- **会话历史留痕** ➜ 将单次交流的重大决断、演进思维梳理并记录至 `docs/session-history.log`（配合 `/doc-update` 工作流操作）。
- **数据字典对齐** ➜ 任何涉及 SQLAlchemy 模型 (`models.py`) 的增删改查，必须通过 `make docs` 等手段刷新 `docs/api/DATA_DICTIONARY.md` 以确保 Schema 真实性。

## 3. 专项开发禁区 (Domain Restrictions)

### 3.1 前端 UI 与代码审查规范
> 🎨 **最高行动指令**：无论需求看似多么简单，所有前端样式、组件抽象开发，必须严格遵守 [`docs/frontend/CONVENTIONS.md`](docs/frontend/CONVENTIONS.md)。**严禁**随意内联硬编码 Hex 色值或引入脱离体系的临时库。

### 3.2 容器化强制验证 (The Container Mandate)
- **环境隔离要求**：不允许以“Windows PowerShell 宿主机无报错”为由声称测试通过。
- **验证生命线**：所有 API 逻辑变动、数据库 Migration，**必须在 Docker 容器内执行验证**（如 `make test` 或 `docker-compose exec api pytest`）。

### 3.3 绝对禁止根目录污染与环境自愈 (Hygiene & Cleanup Enclosure)
- **绝对重定向禁区**：严禁在根目录执行任何非版本控制的文件生成（如 `> report.txt`）。重定向导出必须强制前缀 `tmp/`。
- **完工清扫钩子 (Cleanup Hook)**：在宣告任务完成、提交 `progress.txt` 更新前，必须自发通过 `Remove-Item` 或 `make clean` 清理所有残留的测试、统计相关的临时文件。

## 4. 意图锚准与沟通侧写 (Communication Guardrails)

- **降维解说（小白友好）**：在讲解复杂数据流向、表结构依赖时，预设用户当前精力有限或为“技术小白视角”。大量使用通俗化类比（如：出厂标签、身份证），严禁僵硬堆砌专业术语。
- **物理事实之上**：在提供状态报告时，禁止出现“经过推理代码应该没问题了”之类的幻觉。一切断言必须基于 `git status`, `docker ps`, `pytest` 的真实控制台输出。
- **工具隔离（语义防误伤）**：当用户提议“怎么整”、“帮忙看看”、“有什么方案”等（咨询态）时，AI 严禁在这个回合调用 `write_to_file` 或其他修改命令。必须先给出诸如「选项 A (推荐) / 选项 B (保守)」的结构化分析，待用户显式回复“请按 A 执行”后，方可切换为“执行态”。

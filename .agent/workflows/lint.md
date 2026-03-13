---
description: [lint] 执行全项目代码质量审计，包含 Ruff 静态检查、前端行数限制及全链路对齐规范。
---

# 全项目质量审计 (Comprehensive Lint)

该工作流用于在合并或交付前，对项目进行全方位"宪法"合规性检查。

> **工具链**：项目已统一使用 **Ruff** 作为唯一的 Lint + Format 工具（参见 `contexts.md` 第 18 章）。
> 所有检查以根目录 `ruff.toml` 为准。

## 审计步骤 (Audit Steps)

// turbo
1. **Ruff 代码检查 (Lint)**
   运行 Ruff 检查代码质量与规范合规：
   ```powershell
   make lint
   ```
   - 等价于 `ruff check devops_collector/ devops_portal/ tests/ scripts/`
   - **通过条件**：Exit Code = 0，零错误。
   - 若失败：优先尝试 `make ruff-fix` 自动修复，仍有遗留则手动处理。

// turbo
2. **Ruff 代码格式化检查 (Format)**
   检查代码格式一致性（不自动修改）：
   ```powershell
   ruff format --check devops_collector/ devops_portal/ tests/ scripts/
   ```
   - 若失败：执行 `make fmt` 自动格式化，然后重新 Commit。

3. **前端行数审计 (300 Line Law)**
   检查 HTML/CSS/JS 文件是否超过 300 行：
   ```powershell
   python scripts/lint_frontend.py
   ```

4. **全链路对齐审计 (Naming Alignment)**
   检查新增文件是否包含正确的业务域前缀：
   - Service Desk: `sd_`
   - Administration: `adm_`
   - Project Management: `pm_`
   - Testing / Quality: `qa_`
   - Maintenance: `ops_`
   - Report / Dashboard: `rpt_`
   - System / Infra: `sys_`

5. **依赖导入审计 (Dependency Health)**
   运行环境依赖检查脚本：
   ```powershell
   python scripts/check_imports.py
   ```

## 完工标准 (DoD)
- [ ] `make lint` 输出 0 错误 (Green Build)。
- [ ] 若存在阻塞性错误（如代码无法导入），必须立即修复。
- [ ] 若因架构需求显式忽略规则，需在 `ruff.toml` 或行内 `# noqa` 标注原因。
- [ ] 将审计结论汇总并以表格形式反馈。

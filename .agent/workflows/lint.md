---
description: [lint] 执行全项目代码质量审计，包含 Python 逻辑、前端行数限制及全链路对齐规范。
---

# 全项目质量审计 (Comprehensive Lint)

该工作流用于在合并或交付前，对项目进行全方位“宪法”合规性检查。

## 审计步骤 (Audit Steps)

// turbo
1. **代码格式审计 (Format Check)**
   运行 Black 检查代码格式一致性：
   ```powershell
   black --check devops_collector/ devops_portal/ tests/ scripts/ --line-length=100
   ```

2. **Python 逻辑审计 (Static Analysis)**
   运行 Flake8 和 Pylint 检查代码质量与“300行物理定律”：
   ```powershell
   flake8 devops_collector/ devops_portal/ --max-line-length=100 --statistics
   # Pylint 将执行深度检查，包含 max-module-lines=300
   pylint devops_collector/ devops_portal/
   ```

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

5. **依赖导入审计 (Dependency Health)**
   运行环境依赖检查脚本：
   ```powershell
   python scripts/check_imports.py
   ```

## 完工标准 (DoD)
- [ ] 所有审计项通过，或违规项已被明确列出并制定重构计划。
- [ ] 若存在阻塞性错误（如代码无法导入），必须立即修复。
- [ ] 将审计结论汇总并以表格形式反馈。

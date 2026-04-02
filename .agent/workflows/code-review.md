---
description: [code-review] 标准化代码审查规程，确保变更符合上下文宪法 (contexts.md) 与质量基线。
---

# 代码审查工作流 (Code Review Workflow)

本工作流用于 Agent 在交付功能或发起合并前的“三层深度自审”。

## 第一层：基础自动化审计 (Base Layer - Automated)

// turbo
1. **静态扫描**
   执行完整本地审计流：
   ```powershell
   make lint
   ```
   - **检查点**：Ruff 代码检查（静态逻辑 + 格式化）、文件长度限制 (300行物理定律)。

## 第 1.5 层：风险预判 (Risk Pre-check) — L2 及以上

扫描 `docs/lessons-learned.log`，自动关联与本次变更相关的历史教训：

1. **按 Domain 匹配**：识别本次变更涉及的领域（如 ZenTao、DB、MQ、Auth 等），检索历史记录中同域的 Universal Rule。
2. **交叉验证**：检查本次代码变更是否违反了已有的 Universal Rule（如：是否在循环中调用 `create_engine`？是否直接存储了 `dict` 对象？）。
3. **输出**：在审查报告中增加 `⚠️ 关联教训` 部分，列出相关的防御规则。

## 第二层：架构与宪法合规自查 (Architectural Layer)

手动核对以下“最高准则”：

### 1. Router-Service 模式对齐
- [ ] **Router 层**：是否仅包含参数校验、路由定义、依赖注入及对 Service 的调用？
- [ ] **Service 层**：业务逻辑是否在此层解耦？跨表操作是否使用了原子事务 (`with db.begin():`)？
- [ ] **Response Model**：所有 API 路由是否定义了 Pydantic `response_model`？严禁直接返回 SQLAlchemy 对象。

### 2. 行级权限 (RLS) 与安全
- [ ] **数据隔离**：涉及查询的操作是否通过 `apply_row_level_security` 进行了组织树或个人权限过滤？
- [ ] **审计字段**：新增的模型是否包含了 `created_at`, `updated_at`, `created_by`, `is_deleted`？

### 3. 业务域命名审计 (Naming Alignment Audit) [MANDATORY]

> **动作**：AI 在审查阶段必须显式重读并对齐 [`contexts.md#11.1`](contexts.md#L323) (业务域前缀注册表)。

- [ ] **物理目录/文件名对齐**：
    - 业务模块目录是否使用了正确的前缀？
    - 后端文件是否遵循：`{prefix}_{resource}_router.py` / `{prefix}_{resource}_service.py`？
- [ ] **数据库表对齐**：SQLAlchemy 模型的 `__tablename__` 是否 100% 匹配 `{prefix}_{resource}s`（如 `sd_tickets`）？
- [ ] **前端资源对齐**：CSS Class 是否使用了 `.{prefix}-{component}`？
- [ ] **错误码/Pydantic 模型对齐**：
    - 业务异常代码是否遵循：`{PREFIX}_{ERROR_KEY}`？
    - Pydantic Schema 是否遵循：`{Prefix}{Resource}Schema`？

## 第三层：稳健性与证据链审查 (Robustness Layer)

### 1. 异常与回滚
- [ ] **错误处理**：是否使用了 `BusinessException` 而非直接抛出 `HTTPException`？
- [ ] **向后兼容性**：数据库变更是否遵循“先增列、后改码、后删旧”的顺序？

### 2. 证据验证 (Evidence)
- [ ] **单元测试**：每一个新增的功能函数是否有对应的测试用例（入库 `tests/`）？
- [ ] **回归报告**：是否有最近一次的 `pytest` 运行结果日志（Green Build）？

## 审查结论输出格式

审查完成后，必须按以下格式输出结论：

---
### 🛠️ Code Review 评审报告
- **核心风险评级**：[低/中/高]
- **违规项清单**：若有，请逐项列出；若无，写“无”。
- **架构对齐情况**：[Router-Service 完全对齐/部分偏离]
- **命名审计情况**：[contexts.md#11.1 100% 对齐 / 发现 X 处偏离：(列表说明)]
- **测试通过证据**：[提供 pytest 关键输出或路径]
- **结论**：[允许合并 / 需先重构]
---

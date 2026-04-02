---
description: [plugin-init] 插件工厂工作流 — 标准化创建新数据源集成插件 (GitLab/ZenTao/Jira 等)
---

# 插件工厂工作流 (Plugin Factory Workflow)

> **触发时机**：需要接入新的外部系统（如 Jira, Jenkins, SonarQube）或新增独立的业务域模块。
> **核心目标**：5 分钟内生成合规的 Router-Service-Worker-Bridge 四层架构。

---

## Step 1: 注册与命名规则 (Registry & Naming)

1. **查阅宪法**：AI 必须首先打开 [`contexts.md#11.1`](contexts.md#L323)，检查是否已经存在该业务域的前缀。
   - 若不存在：提议一个新的 2-3 字母前缀（如 `jr_` 代表 Jira）。
   - 若存在：严格执行。

2. **核心元数据定义**：
   - Prefix: `[prefix]_`
   - Domain Component: `[component_name]`
   - Source System: `[system_id]`

## Step 2: 骨架生成 (Scaffolding)

AI 在执行 `/plugin-init` 时，必须按以下标准结构生成文件（不得缺失）：

### 📂 1. 后端 - 业务逻辑层 (Business Layer)
- `devops_collector/plugins/[prefix]_[component]/service.py` -> 核心业务逻辑
- `devops_collector/plugins/[prefix]_[component]/bridge.py` -> 数据桥接与适配
- `devops_collector/plugins/[prefix]_[component]/worker.py` -> 异步采集任务

### 📂 2. 后端 - API 接口层 (API Gateway)
- `devops_portal/routers/[prefix]_[component]_router.py` -> 仅限路由、参数校验、Response Model。

### 📂 3. 数据持久层 (Persistence)
- 在 `devops_collector/models/` 下创建模型文件。
- **强制约束**：必须包含 `id` (BigInt), `source_id`, `created_at` 等 mdm 基础字段，符合 [`contexts.md#5`](contexts.md#L91)。

### 📂 4. 自动化测试 (Testing)
- `tests/plugins/[prefix]_[component]/test_worker.py` -> Worker 采集模拟。
- `tests/plugins/[prefix]_[component]/test_router.py` -> Router 接口模拟。

---

## Step 3: 手动集成与注册 (Manual Wiring)

1. 在 `devops_portal/main.py` 中注册 `router`。
2. 在 `devops_collector/core/worker_factory.py` 中注册 `worker` 任务。
3. 执行 `make migrations` 生成 Alembic 脚本。

## Step 4: 冒烟测试 (Smoke Test)

// turbo
1. 执行 `make lint` 确保命名完全对齐。
2. 运行基础 mock 测试：`pytest tests/plugins/[prefix]_[component]/`。

---

## 完工签章

在回复中包含：
```
[Plugin Init Complete] Domain: [Name] | Prefix: [xx_] | Scaffolding: 6 files generated | Ready for dbt modeling
```

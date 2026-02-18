# DevOps 平台 - 进展归档 (Progress Archive)

> 从 `progress.txt` 归档的已完成任务。按时间倒序排列。

---

## 归档批次：2026-02-18

以下 15 条任务从 `progress.txt` 迁移至此归档。

### 15. [Process] Development Process Alignment (2026-02-18)
- **宪章更新**: 更新 `contexts.md` 强制 Validation First 和 Evidence-Based Delivery。
- **工作流**: 创建 `.agent/workflows/lint.md` 和 `code-review.md`。
- **工具链**: 新增 `scripts/lint_frontend.py` 执行 300 行定律。

### 14. [P1] Dependency Check CI Integration (2026-02-17)
- **Schema**: Enhanced `DependencyScan` with CI context (`job_url`, `commit_sha`) & False Positive support.
- **Worker**: Refactored to support pure JSON import via API, removed legacy local scan logic.
- **API**: Implemented `POST /api/security/dependency-check/upload` endpoint in Portal.
- **Cleanup**: Deleted unused `client.py` and old tests.

### 13. [P2] 测试目录结构重构 (2026-02-17)
- **重组**: 75 个文件归并为 `unit/`, `integration/`, `e2e/`, `scripts/` 四层结构。
- **清理**: 删除 `tests/simulations/` (弃用脚本) 和 `tests/analytics/` (过时 DORA 测试)。
- **规范**: 统一 `test_*.py` 命名，更新 Makefile (`test-all`)，明确 pyproject.toml testpaths。
- **Tech Debt**: 发现并登记 7 个既有 broken tests (Backlog P3)。

### 12. [P1] 分支合并：将 `feat/zt-task-effort` Squash Merge 到 `main` (2026-02-17)
- 已通过: Rebase + 本地单元测试 (20/20 passed, PYTHONPATH=.) + 安全性自检。
- 降级: 未执行 `make test` (镜像缺失) / `make deploy` (网络超时)。
- 阻塞原因: 离线环境与 Docker 镜像加速地址失效导致无法重新构建镜像。

### 11. [P0] 修复核心测试套件 (Core Test Suite Fixes)
- **Product Flow**：修复 `test_product_flow.py` 中项目/产品关联逻辑的 404/None 错误。
- **Main API**：修复 `test_main.py` 中 Pydantic Schema 字段不匹配导致的数据校验错误。
- **Integration Tests**：修复 Mock Generator 返回类型错误、`TestClient` 鉴权失败及依赖覆盖互相干扰。
- **Refactoring**：统一了 integration 测试的 `client` fixture 实现，消除了全局状态污染。
- **结果**：`tests/unit/devops_portal/` 及 `tests/integration/` 全量通过。

### 10. [P1] 单元测试全量修复 (Unit Test Infrastructure Fix)
- **GitLab Client**：补充缺失的 `get_project_issue()` 方法。
- **QA 测试修复**：修正 `test_execute_test_case` 中 `update_issue` 参数断言方式。
- **ORM Mapper 修复**：为 `SonarProject` 补充 `gitlab_project_id` 列和关系；为 `ZenTaoIssue` 复合主键添加显式 `foreign_keys`。
- **测试 Fixture 修复**：为 `tests/unit/` 新增 `conftest.py`，提供 `db_session` fixture。
- **结果**：`make test-local` 全部 **20 passed, 0 failed, 0 errors** ✅

### 9. [P1] Jenkins 部署效能穿透与 DORA 指标 (Jenkins & DORA)
- **模型扩展**：为 `JenkinsJob` 增加 MDM 关联及部署标识位。
- **拓扑关联**：实现 `init_jenkins_links.py`，支持 Folder 级路径继承。
- **效能建模**：在 dbt 中实现 DORA 核心指标事实表 `fct_dora_deployment_frequency`。
- **验证**：通过 `dbt compile` 全量解析。

### 8. [P1] SonarQube 深度集成与质量门禁 (SonarQube Integration)
- **模型扩展**：为 `SonarProject` 增加 MDM 资产物理引脚，`SonarMeasure` 新增增量代码指标。
- **拓扑关联**：创建 `init_sonarqube_links.py`，支持通过 CSV 进行显式业务对齐。
- **指标建模**：在 dbt 中实现 `int_sonar_project_quality` 指标看板中间层。
- **验证**：通过 `dbt compile` 语法与血缘校验。

### 7. [P1] 禅道 20.0 架构兼容与主数据关联 (MDM Integration)
- **层级支持**：在 `ZenTaoExecution` 中引入 `parent_id` 和 `path` 字段，适配树状结构。
- **关联机制**：实现 `init_zentao_links.py`，支持基于 `path` 路径的 MDM 项目归属自动继承。
- **质量追溯**：实现发布->计划和用例->需求的自动化全链路穿透逻辑（待确认方案）。
- **文档闭环**：通过 `make docs` 动态刷新 `DATA_DICTIONARY.md`。

### 6. [P1] 禅道插件增强：任务与工时采集 (ZenTao Task & Effort)
- **模型扩展**：升级 `ZenTaoIssue` 支持 `task` 类型，新增复合主键和工时字段。
- **采集实现**：增强 `ZenTaoClient` 和 `ZenTaoWorker`，支持全量 Task 同步。
- **配置对齐**：将 `zentao` 配置集成到全局 `Settings` (Pydantic V2)。
- **验证工具**：创建 `scripts/sync_zentao.py` 专用同步验证脚本。

### 5. [P0] 完善项目开发宪章 (Contexts Enhancement)
- 在 `contexts.md` 中新增第14章 "软件交付生命周期 (SDLC)"，明确了需求状态流转、RFC 设计门禁、安全左移策略及 DoD 标准。

### 4. [P0] 数据库重置与部署验证
- 实现了 `scripts/reset_database.py`，支持开发环境一键清空并重建数据。
- 已验证手动重启容器后的功能一致性。

### 3. [P1] CSV 人员字段双格式支持 & 组织架构重构
- 所有 init 脚本统一使用 `resolve_user()` 工具函数，CSV 人员字段同时支持邮箱和汉字全名。
- 组织架构层级重构：移除 `SYS-体系` 层级节点，层级改为 公司→中心→部门。

### 2. [P1] 数据治理与脚本健壮性 (Data Resilience)
- 修复了 `init_catalog.py` 报错和 `init_gitlab_mappings.py` 崩溃。
- 验证了全量 `make init` 流程，所有 15+ 初始化脚本全部 100% 通过。

### 1. [P1] OKR 数据管理与导出 (OKR Export)
- 实现了后端 API、前端 OKR 治理中心、数据规范和 E2E 测试闭环。
- 通过单元测试、独立验证脚本及 Playwright E2E 测试。

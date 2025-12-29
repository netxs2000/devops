# DevOps 效能平台知识转移手册 (Knowledge Transfer Guide)

**版本**: v1.0.0 (2025-12-27)  
**保密等级**: 内部公开  
**核心目标**: 帮助新开发者快速上手，理解系统架构、设计哲学及工程标准。

---

## 1. 项目愿景与设计哲学 (Vision & Philosophy)

### 1.1 项目愿景
打造企业级“产研透明化驾驶舱”，解决数据分散、指标主观、协作黑盒三大痛点。通过自动化数据采集与模型化分析，量化研发效能 (DORA/SPACE) 与业务价值 (ROI/FinOps)。

### 1.2 核心理念
- **ELT (Extract-Load-Transform)**: Python 负责高效搬运原始数据 (Raw Data)，SQL Views 负责灵活承载业务逻辑 (Analytics-in-Database)。
- **插件化架构**: 微内核设计，所有外部工具 (GitLab, Sonar, Jira) 均通过解耦的插件集成。
- **统一身份对齐**: 通过 Email 策略实现多系统账号的一键归并 (Unified Identity)。

---

## 2. 系统架构 (System Architecture)

### 2.1 四层数据流模型
1.  **采集层 (Collector Layer)**: 异步任务驱动，通过插件化的 Worker 调用外部 API。
2.  **暂存层 (Raw Data Staging)**: “先落盘，后解析”，保留 API 原始响应，支持数据历史回放。
3.  **核心事实存储 (Core DB)**: 标准化后的实体模型 (Commits, Issues, MRs, OKRs)。
4.  **数据集市 (Analytics Mart)**: 基于 SQL 视图的战略看板 (PMO/HR/Team Dashboard)。

### 2.2 技术栈
- **后端**: Python 3.x (Pydantic / SQLAlchemy / FastAPI)
- **存储**: PostgreSQL 12+ (利用 JSONB 存储半结构化数据)
- **调度**: APScheduler + RabbitMQ (内部解耦)
- **工程化**: Makefile + GitLab CI/CD

---

## 3. 工程三板斧 (Engineering Standards)

我们强制执行以下标准，确保代码具备企业级质量：

### 3.1 编码规范: Google Python Style Guide
- 所有代码必须符合 Google Python 风格。
- **Docstrings**: 强制使用 Google 格式（包含 Args, Returns, Raises）。
- **工具**: 运行 `make lint` 和 `make format` 自动对齐。

### 3.2 包管理: PEP 518/621
- **`pyproject.toml`**: 项目配置的中枢。
- **`requirements.txt`**: 生产依赖，严格锁定版本。
- **`requirements-dev.txt`**: 开发/测试工具集。

### 3.3 自动化流水线 (CI/CD)
- 每次提交触发代码质量检查 (Linter) 和单元测试 (Pytest)。
- 支持自动化依赖扫描 (OWASP Dependency-Check)。

---

## 4. 核心模块导引 (Core Module Guide)

### 4.1 `devops_collector.core` (系统大脑)
- **`BaseClient`**: 封装了自动重试、速率限制 (Token Bucket) 和认证逻辑。
- **`BaseWorker`**: 提供了数据状态转换和 `save_to_staging` 幂等存贮逻辑。
- **`IdentityManager`**: 核心算法，根据多级策略识别“谁是谁”。
- **`Algorithms`**: 计算 Cycle Time, Lead Time 的纯净物理公式集。

### 4.2 `devops_collector.plugins` (扩展能力)
- **GitLab**: 覆盖了从 Commit 到 Deployment 的全链路采集。
- **FinOps/ROI**: `ResourceCost` 模型与财务对齐方案。
- **OKR**: `OKRService` 支持根据实时采集的度量指标自动刷新战略进度。

---

## 5. 开发实战：如何开发一个新插件

1.  **定义模型**: 在插件目录下创建 `models.py`，继承 `Base`。
2.  **实现客户端**: 继承 `BaseClient`，实现 `test_connection`。
3.  **编写 Worker**: 继承 `BaseWorker`，重写 `process_task`，调用 `save_to_staging`。
4.  **注册插件**: 在 `devops_collector/core/registry.py` 或插件初始化中完成注册。
5.  **编写 DDL**: 为分析逻辑编写 SQL 视图并放入 `migrations/`。

---

## 6. 运维与验证 (DevOps & Verification)

### 6.1 常用命令 (Makefile)
- `make install-dev`: 初始化开发环境。
- `make test-cov`: 运行测试并查看覆盖率报表。
- `make run-worker`: 手动启动采集任务。

### 6.2 数据质量守门员
- 运行 `python scripts/verify_data_integrity.py` 验证 API 与数据库的记录一致性。
- 检查 `logs/` 目录下各插件的同步日志。

### 6.3 数据库清理
- `RetentionManager` 每 24 小时根据配置清理过期的 Staging 原始数据。

---

## 7. 未来路标 (Roadmap)

1.  **AI Enrichment**: 接入 LLM 对 MR 和 Commit 进行语义分类，量化“技术资产率”。
2.  **FinOps 深度集成**: 实现在 Grafana 上的 IT 成本与业务产出的 ROI 关联实时视图。
3.  **前端门户**: 构建基于 Vite/Vue3 的标准化效能大屏。

---

## 8. 重要资源
- [技术架构详解](./architecture/ARCHITECTURE.md)
- [数据字典定义](./api/DATA_DICTIONARY.md)
- [指标算法说明](./guides/指标定义说明.md)

---
*DevOps Team, 2025*

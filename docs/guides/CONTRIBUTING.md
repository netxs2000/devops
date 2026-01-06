# 开发者与贡献指南 (Contributing Guide)

感谢您有兴趣为 DevOps Data Collector 贡献代码！

## 1. 开发规范 (Development Standards)

### 1.1 代码风格与质量

* 严格遵循 **Google Python Style Guide**。
* **语言与符号**:
  * 项目文档的主体语言必须是中文。
  * **严禁**在文件名称、文件内容、注释及 UI 界面出现表情符号。
* **Docstring 规范**: 所有类、方法及核心代码必须包含 **Google Style Docstrings**（中文）。
  * 必须包含 `Attributes` 或 `Args`/`Returns` 节段。
  * 每一项必须包含类型标注，如 `attr_name (type): description`。
* **模型命名原则**: 为了避免与测试框架（如 pytest）发生自动收集冲突，所有测试管理相关的核心模型必须加 `GTM` 前缀（例如：`GTMTestCase`、`GTMRequirement`）。
* **调试友好性**: 所有 ORM 模型类必须实现结构化的 `__repr__` 方法，包含关键识别字段。
* **高内聚，低耦合**: 代码应以模块化方式生成，实现高内聚，低耦合；功能逻辑应尽量下沉至 Service 或 Utility 层。
* **配置外部化**: API 地址、Token 及公共参数必须通过配置文件（如 `config.ini`）获取，严禁硬编码。

### 1.2 提交规范 (Commit Message)

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

* `feat: ...` 新功能
* `fix: ...` 修复 Bug
* `docs: ...` 文档变更
* `refactor: ...` 代码重构
* `chore: ...` 构建/依赖杂项

### 1.3 架构原则

1. **ELT 模式**: 采集中优先拉取原始数据入库 (`raw_data_staging`)，再在数据库中通过视图 (SQL Views) 实现业务逻辑转换。
2. **异步解耦**: 耗时任务（如全量同步）应通过 RabbitMQ 分发至 Worker 执行。

---

## 2. 插件开发规范 (Developing Plugins)

系统采用插件工厂模式。若要新增数据源（如飞书、钉钉、JFrog）：

### 2.1 目录结构

在 `plugins/` 目录下创建新文件夹，必须包含：

* `client.py`: 封装 API 请求逻辑。
* `worker.py`: 实现具体的采集与转换流程。
* `models.py`: 定义当前插件特有的数据库表。

### 2.2 注册插件

必须在 `devops_collector/core/registry.py` (或对应的 Registry 模块) 中注册您的 Worker 和 Client 类，以利用系统自动分发能力。

### 2.3 关键逻辑准则

* **身份归一化**: 严禁直接在插件中创建 User。必须调用 `IdentityManager.get_or_create_user()`，通过 Email 或工号进行全局对齐。
* **原始数据暂存**: 采集到的 JSON 数据必须优先通过 `save_to_staging` 方法保存，以支持数据回放 (Data Replay)。
* **断点续传**: 在 `worker.py` 中记录同步偏移量（如时间戳或 Page），确保任务中断后可恢复。

---

## 3. 测试与验证 (Testing)

### 3.1 仿真测试 (Simulation)

新插件开发完成后，应在 `tests/simulations/` 下增加对应的模拟场景，验证在模拟 API 返回下的数据库一致性。

### 3.2 逻辑重演

使用 `scripts/reprocess_staging_data.py` 验证 Transform 逻辑对历史 Staging 数据的解析正确性。

### 3.3 文档同步

任何的功能变更或 Schema 修改，必须同步更新：

* `DATA_DICTIONARY.md` (物理层)
* `PROJECT_SUMMARY_AND_MANUAL.md` (功能说明)
* `CHANGELOG.md` (版本记录)

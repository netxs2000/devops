# 开发者与贡献指南 (Contributing Guide)

感谢您有兴趣为 DevOps Data Collector 贡献代码！

## 1. 开发规范 (Development Standards)

### 1.1 代码风格
*   严格遵循 **Google Python Style Guide**。
*   所有函数和类必须包含 **Docstring** (Google format)。
*   使用 4 空格缩进，禁止 Tab。

### 1.2 提交规范 (Commit Message)
遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：
*   `feat: ...` 新功能
*   `fix: ...` 修复 Bug
*   `docs: ...` 文档变更
*   `refactor: ...` 代码重构
*   `chore: ...` 构建/依赖杂项

### 1.3 数据库迁移
目前尚未引入 Alembic。如果修改了 `models/` 下的表结构：
1. 请更新 `DATA_DICTIONARY.md`。
2. 请在 Pull Request 中附带 `ALTER TABLE` SQL 语句。

## 2. 如何开发新插件 (Developing Plugins)

如果您想接入新的数据源（如 Jenkins），请遵循以下步骤：

### 2.1 目录结构
在 `plugins/` 目录下创建新文件夹，例如 `plugins/jenkins/`。
需包含：
*   `__init__.py`
*   `collector.py`: 核心逻辑
*   `models.py`: 独有的数据模型

### 2.2 实现接口
参考 `plugins/gitlab/collector.py`，您的 Collector 类通常需要包含：
*   `sync()`: 入口方法。
*   `process_data()`: 数据处理。
*   `save()`: 持久化。

### 2.3 数据关联
*   **必须**使用 `models.base_models.User` 关联用户。
*   **必须**使用 `models.base_models.Organization` 关联组织。

## 3. 测试指南 (Testing)

### 3.1 运行测试
（目前项目单元测试建设中，建议优先编写集成测试脚本）

可以在 `scripts/` 下创建 `verify_jenkins.py` 类似的脚本，手动验证数据是否正确入库。

### 3.2 静态检查
提交前请运行 pylint 或 flake8：
```bash
flake8 devops_collector plugins scripts
```

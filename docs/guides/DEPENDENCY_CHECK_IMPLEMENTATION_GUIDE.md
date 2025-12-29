# OWASP Dependency-Check 集成实施指南

## ✅ 已完成的工作

我已经为您创建了以下文件：

### 1. 数据库迁移脚本
**文件**: `devops_collector/plugins/dependency_check/add_dependency_check_tables.sql`
- ✅ 创建 4 个核心表（dependency_scans, dependencies, dependency_cves, license_risk_rules）
- ✅ 创建所有必要的索引
- ✅ 预置 16 个常见开源许可证规则
- ✅ 创建增强的许可证合规性分析视图

### 2. SQLAlchemy 数据模型
**文件**: `devops_collector/models/dependency.py`
- ✅ DependencyScan 模型
- ✅ Dependency 模型
- ✅ DependencyCVE 模型
- ✅ LicenseRiskRule 模型
- ✅ 所有关系映射（relationships）

### 3. 集成方案文档
**文件**: `OWASP_DEPENDENCY_CHECK_INTEGRATION.md`
- ✅ 完整的数据模型设计说明
- ✅ Worker 实现代码示例
- ✅ 配置文件示例
- ✅ 使用指南

---

## 📋 您需要完成的步骤

### 步骤 1: 执行数据库迁移

```bash
# 连接到您的 PostgreSQL 数据库
psql -h localhost -U your_user -d devops_db

# 执行迁移脚本
\i devops_collector/plugins/dependency_check/add_dependency_check_tables.sql

# 验证表创建成功
\dt dependency*
\dt license_risk_rules

# 查看预置的许可证规则
SELECT license_name, risk_level, is_copyleft FROM license_risk_rules;
```

### 步骤 2: 更新模型导入

在 `devops_collector/models/__init__.py` 中添加：

```python
from .dependency import DependencyScan, Dependency, DependencyCVE, LicenseRiskRule

__all__ = [
    # ... 现有模型 ...
    'DependencyScan',
    'Dependency',
    'DependencyCVE',
    'LicenseRiskRule',
]
```

### 步骤 3: 更新 Project 模型

在 `devops_collector/models/project.py` 的 `Project` 类中添加关系：

```python
class Project(Base):
    # ... 现有字段 ...
    
    # 新增关系
    dependency_scans = relationship('DependencyScan', back_populates='project')
    dependencies = relationship('Dependency', back_populates='project')
```

### 步骤 4: 安装 OWASP Dependency-Check（可选）

如果您想立即测试扫描功能：

```bash
# 下载最新版本
wget https://github.com/jeremylong/DependencyCheck/releases/download/v8.4.0/dependency-check-8.4.0-release.zip

# 解压
unzip dependency-check-8.4.0-release.zip

# 测试安装
./dependency-check/bin/dependency-check.sh --version
```

### 步骤 5: 更新配置文件（可选）

在 `config.ini` 中添加：

```ini
[dependency_check]
# OWASP Dependency-Check CLI 路径
cli_path = /path/to/dependency-check/bin/dependency-check.sh

# 扫描超时时间（秒）
timeout = 600

# 是否启用自动扫描
auto_scan_enabled = false

# 扫描频率（天）
scan_frequency_days = 7
```

---

## 🎯 下一步计划（可选）

如果您希望我继续实现 Worker 代码，我可以为您创建：

1. **DependencyCheckClient** - 封装 OWASP Dependency-Check CLI 调用
2. **DependencyCheckWorker** - 完整的数据采集器
3. **单元测试** - 测试用例
4. **文档更新** - 更新 DATA_DICTIONARY.md 和 PROJECT_SUMMARY_AND_MANUAL.md

**是否需要我继续实现 Worker 代码？**

---

## ✅ 验证清单

完成上述步骤后，请验证：

- [ ] 数据库表创建成功
- [ ] 许可证规则已预置（应该有 16 条记录）
- [ ] Python 模型可以正常导入
- [ ] 视图 `view_compliance_oss_license_risk_enhanced` 创建成功

验证命令：

```python
# 测试模型导入
from devops_collector.models import DependencyScan, Dependency, DependencyCVE, LicenseRiskRule

# 测试数据库连接
from devops_collector.core.database import get_session

with get_session() as session:
    count = session.query(LicenseRiskRule).count()
    print(f"许可证规则数量: {count}")  # 应该输出 16
```

---

## 📞 需要帮助？

如果遇到任何问题，请告诉我：
- 数据库迁移错误
- 模型导入问题
- 需要我继续实现 Worker 代码

**当前状态**: 数据层已完成 ✅，等待您的反馈以继续实现业务逻辑层。

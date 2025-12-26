# OWASP Dependency-Check 持久化存储配置指南

## ✅ 已完成的更新

我已经为您更新了 Worker 代码，现在支持：

1. ✅ **持久化报告存储** - 报告保存到配置的目录，长期保留
2. ✅ **导入已有报告** - 支持导入历史报告文件
3. ✅ **自动清理过期报告** - 根据配置的保留天数自动清理

---

## 📁 目录结构

### 默认报告存储结构

```
/var/lib/devops/dependency-reports/
├── my-project/
│   ├── 1/                          # scan_id = 1
│   │   └── dependency-check-report.json
│   ├── 2/                          # scan_id = 2
│   │   └── dependency-check-report.json
│   └── 3/                          # scan_id = 3
│       └── dependency-check-report.json
├── another-project/
│   ├── 4/
│   │   └── dependency-check-report.json
│   └── 5/
│       └── dependency-check-report.json
└── project_123/                    # 未提供 project_name 时使用 project_id
    └── 6/
        └── dependency-check-report.json
```

**优点**：
- ✅ 按项目组织，便于管理
- ✅ 按 scan_id 隔离，避免冲突
- ✅ 易于追溯和审计

---

## ⚙️ 配置文件

### 在 `config.ini` 中添加：

```ini
[dependency_check]
# OWASP Dependency-Check CLI 路径
cli_path = /usr/local/bin/dependency-check.sh

# 扫描超时时间（秒）
timeout = 600

# 报告存储目录（持久化路径）
report_dir = /var/lib/devops/dependency-reports

# 是否保留报告文件
keep_reports = true

# 报告保留天数（0 表示永久保留）
report_retention_days = 90

# 是否启用自动扫描
auto_scan_enabled = false

# 自动扫描频率（天）
scan_frequency_days = 7
```

### Windows 环境配置示例：

```ini
[dependency_check]
cli_path = C:\Tools\dependency-check\bin\dependency-check.bat
timeout = 600
report_dir = C:\DevOps\dependency-reports
keep_reports = true
report_retention_days = 90
```

---

## 🚀 使用示例

### 1. 执行新扫描（自动保存到持久化目录）

```python
from devops_collector.plugins.dependency_check import DependencyCheckWorker
from devops_collector.core.config import load_config

# 加载配置
config = load_config('config.ini')

# 初始化 Worker
worker = DependencyCheckWorker(config)

# 扫描项目
scan_id = worker.run_scan(
    project_id=123,
    project_path='C:\\Projects\\my-app',
    project_name='my-app'
)

print(f"✅ 扫描完成！Scan ID: {scan_id}")
print(f"📁 报告位置: /var/lib/devops/dependency-reports/my-app/{scan_id}/")
```

### 2. 导入已有报告

```python
# 导入单个历史报告
scan_id = worker.import_existing_report(
    project_id=123,
    report_path='C:\\Reports\\old-scan\\dependency-check-report.json',
    project_name='my-app'
)

print(f"✅ 导入完成！Scan ID: {scan_id}")
```

### 3. 批量导入历史报告

```python
from pathlib import Path

def batch_import_reports(worker, project_id, project_name, reports_dir):
    """批量导入历史报告"""
    reports_path = Path(reports_dir)
    imported = 0
    failed = 0
    
    for report_file in reports_path.rglob('dependency-check-report.json'):
        try:
            scan_id = worker.import_existing_report(
                project_id=project_id,
                project_name=project_name,
                report_path=str(report_file)
            )
            print(f"✅ Imported: {report_file.parent.name} -> Scan ID: {scan_id}")
            imported += 1
        except Exception as e:
            print(f"❌ Failed: {report_file} -> {e}")
            failed += 1
    
    print(f"\n📊 Summary: {imported} imported, {failed} failed")

# 使用
batch_import_reports(
    worker=worker,
    project_id=123,
    project_name='my-app',
    reports_dir='C:\\HistoricalReports\\my-app'
)
```

### 4. 清理过期报告

```python
# 先预览要删除的文件（dry run）
stats = worker.cleanup_old_reports(dry_run=True)
print(f"将删除 {stats['deleted_count']} 个目录，释放 {stats['freed_space_mb']} MB 空间")

# 确认后执行实际清理
stats = worker.cleanup_old_reports(dry_run=False)
print(f"✅ 已删除 {stats['deleted_count']} 个目录，释放 {stats['freed_space_mb']} MB 空间")
```

### 5. 定时清理任务（Cron Job）

```python
# cleanup_reports.py
from devops_collector.plugins.dependency_check import DependencyCheckWorker
from devops_collector.core.config import load_config
import logging

logging.basicConfig(level=logging.INFO)

config = load_config('config.ini')
worker = DependencyCheckWorker(config)

# 执行清理
stats = worker.cleanup_old_reports(dry_run=False)

print(f"Cleanup completed:")
print(f"  - Deleted: {stats['deleted_count']} directories")
print(f"  - Freed: {stats['freed_space_mb']} MB")
```

**添加到 Cron**：
```bash
# 每周日凌晨 2 点执行清理
0 2 * * 0 cd /path/to/devops_collector && python cleanup_reports.py >> /var/log/dependency-check-cleanup.log 2>&1
```

---

## 📊 查询报告位置

### SQL 查询

```sql
-- 查看所有扫描记录及其报告路径
SELECT 
    ds.id as scan_id,
    p.name as project_name,
    ds.scan_date,
    ds.report_path,
    ds.total_dependencies,
    ds.vulnerable_dependencies
FROM dependency_scans ds
JOIN projects p ON ds.project_id = p.id
ORDER BY ds.scan_date DESC
LIMIT 10;

-- 查看特定项目的最新扫描报告
SELECT report_path
FROM dependency_scans
WHERE project_id = 123
ORDER BY scan_date DESC
LIMIT 1;
```

### Python 查询

```python
from devops_collector.models import DependencyScan, Project
from devops_collector.core.database import get_session

with get_session() as session:
    # 查询最新扫描
    latest_scan = session.query(DependencyScan)\
        .filter_by(project_id=123)\
        .order_by(DependencyScan.scan_date.desc())\
        .first()
    
    if latest_scan:
        print(f"最新扫描报告: {latest_scan.report_path}")
        print(f"扫描时间: {latest_scan.scan_date}")
        print(f"依赖总数: {latest_scan.total_dependencies}")
```

---

## 🔧 高级配置

### 自定义报告目录结构

如果您希望按日期组织报告：

```python
# 修改 worker.py 中的 run_scan 方法
from datetime import datetime

# 目录结构: /var/lib/devops/dependency-reports/{project_name}/{YYYY-MM-DD}/{scan_id}
date_str = datetime.now().strftime('%Y-%m-%d')
output_dir = f"{self.report_base_dir}/{project_name}/{date_str}/{scan_id}"
```

### 报告压缩存储

如果磁盘空间有限，可以在扫描完成后压缩报告：

```python
import gzip
import shutil

def compress_report(report_path):
    """压缩报告文件"""
    with open(report_path, 'rb') as f_in:
        with gzip.open(f"{report_path}.gz", 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    # 删除原文件
    os.remove(report_path)
    
    return f"{report_path}.gz"

# 在 run_scan 方法中使用
compressed_path = compress_report(report_path)
scan.report_path = compressed_path
```

---

## ✅ 验证清单

完成配置后，请验证：

- [ ] 配置文件已更新（`config.ini`）
- [ ] 报告目录已创建（`/var/lib/devops/dependency-reports`）
- [ ] 目录权限正确（可读写）
- [ ] 成功执行一次扫描
- [ ] 报告文件已保存到配置的目录
- [ ] 数据库中 `report_path` 字段正确
- [ ] 清理功能正常工作（dry run 测试）

---

## 📞 常见问题

### Q1: 报告目录权限不足怎么办？

```bash
# 创建目录并设置权限
sudo mkdir -p /var/lib/devops/dependency-reports
sudo chown -R your_user:your_group /var/lib/devops/dependency-reports
sudo chmod -R 755 /var/lib/devops/dependency-reports
```

### Q2: 如何迁移已有的临时报告到持久化目录？

```python
import shutil
from pathlib import Path

def migrate_reports(old_dir, new_base_dir):
    """迁移报告文件"""
    old_path = Path(old_dir)
    
    for scan_dir in old_path.iterdir():
        if scan_dir.is_dir():
            scan_id = scan_dir.name
            # 假设从数据库查询到 project_name
            new_path = Path(new_base_dir) / 'migrated' / scan_id
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(scan_dir, new_path)
            print(f"Migrated: {scan_dir} -> {new_path}")

migrate_reports('/tmp/dependency-check-reports', '/var/lib/devops/dependency-reports')
```

### Q3: 如何监控报告目录的磁盘使用？

```python
def get_reports_disk_usage(report_dir):
    """获取报告目录的磁盘使用情况"""
    from pathlib import Path
    
    total_size = 0
    file_count = 0
    
    for file_path in Path(report_dir).rglob('*'):
        if file_path.is_file():
            total_size += file_path.stat().st_size
            file_count += 1
    
    return {
        'total_size_mb': round(total_size / 1024 / 1024, 2),
        'file_count': file_count
    }

# 使用
usage = get_reports_disk_usage('/var/lib/devops/dependency-reports')
print(f"报告目录占用: {usage['total_size_mb']} MB, {usage['file_count']} 个文件")
```

---

**🎉 配置完成！您的报告现在会持久化保存到配置的目录中！**

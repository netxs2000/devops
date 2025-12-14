# 部署与运维手册 (Deployment & Operations Guide)

## 1. 部署环境要求 (Prerequisites)

### 硬件建议
*   **CPU**: 2 Core+
*   **Memory**: 4GB+ (大型项目全量同步时内存消耗较大)
*   **Disk**: 50GB+ (取决于 Git 仓库数量和提交历史长度)

### 软件依赖
*   **OS**: Linux (Ubuntu 20.04+, CentOS 7+) / Windows Server
*   **Runtime**: Python 3.9+
*   **Database**: PostgreSQL 12+ (强烈建议，不推荐生产环境使用 SQLite)

## 2. 安装步骤 (Installation)

### 2.1 获取代码
```bash
git clone https://gitlab.example.com/devops/devops_collector.git
cd devops_collector
```

### 2.2 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate  # Linux
# venv\Scripts\activate   # Windows
```

### 2.3 安装依赖
```bash
pip install -r requirements.txt
```

### 2.4 数据库初始化
```bash
# 1. 登录 PostgreSQL 创建数据库
psql -U postgres -c "CREATE DATABASE devops_db;"

# 2. 运行初始化脚本 (自动建表)
python scripts/init_discovery.py
```

## 3. 配置详解 (Configuration)

配置文件路径: `config.ini`

### [database]
| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `url` | SQLAlchemy 数据库连接串 | `postgresql://user:pass@host:5432/dbname` |

### [gitlab]
| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `url` | GitLab 实例地址 | `https://gitlab.company.com` |
| `token` | 具有 `api` 权限的 Personal Access Token | `glpat-xxxxxxxx` |
| `nop_token` | (可选) 备用 Token，主 Token 限流时切换 | `glpat-yyyyyyyy` |

### [sonarqube]
| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `url` | SonarQube 实例地址 | `https://sonar.company.com` |
| `token` | 用户 Token | `squ_xxxxxxxx` |

### [common]
| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `org_name` | 顶层组织名称，用于报表标题 | `MyTechCorp` |

## 4. 定时任务配置 (Scheduling)

建议使用 Crontab 进行任务调度。

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 1 点执行全量发现 (发现新项目)
0 1 * * * cd /path/to/app && venv/bin/python scripts/init_discovery.py >> logs/discovery.log 2>&1

# 每小时执行增量同步 (抓取新 Commit)
0 * * * * cd /path/to/app && venv/bin/python -m devops_collector.main >> logs/sync.log 2>&1

# 每天凌晨 3 点同步 SonarQube 数据
0 3 * * * cd /path/to/app && venv/bin/python scripts/sonarqube_stat.py >> logs/sonar.log 2>&1
```

## 5. 常见问题排查 (Troubleshooting)

### Q: 初始化时报错 "FATAL: password authentication failed"
*   **原因**: 数据库密码错误或 pg_hba.conf 未允许连接。
*   **解决**: 检查 `config.ini` 中的数据库 URL，确保用户名密码正确且有建表权限。

### Q: GitLab 同步极慢或卡住
*   **原因**: 某些项目 Commit 历史过长 (如 10w+)。
*   **解决**: 
    1. 检查日志查看卡在哪个 Project ID。
    2. 系统会自动记录断点，杀掉进程重启后会从断点处继续，不要为了速度频繁重启。
    3. 检查网络带宽。

### Q: SonarQube 数据为空
*   **原因**: 项目 Key 匹配失败。
*   **解决**: 
    *   默认匹配规则是 `GitLab Path With Namespace` == `Sonar Project Key`。
    *   如果规则不同，需修改 `plugins/sonarqube/collector.py` 中的 `_resolve_project_key` 逻辑。

## 6. 升级维护 (Maintenance)

### 备份数据
```bash
pg_dump -U username devops_db > backup_$(date +%Y%m%d).sql
```

### 代码更新
```bash
git pull
pip install -r requirements.txt  # 依赖可能变更
# 如果有 Schema 变更，目前需手动执行 SQL（后续版本引入 Alembic）
```

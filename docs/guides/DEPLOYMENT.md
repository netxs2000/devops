# 部署与运维手册 (Deployment & Operations Guide)

**版本**: 3.8.0
**日期**: 2026-01-01

## 1. 部署环境要求 (Prerequisites)

### 硬件建议

* **CPU**: 2 Core+
* **Memory**: 4GB+ (大型项目全量同步时内存消耗较大)
* **Disk**: 50GB+ (取决于 Git 仓库数量和提交历史长度)

### 软件依赖

* **OS**: Linux (Ubuntu 20.04+, CentOS 7+) / Windows Server
* **Runtime**: Python 3.9+
* **Database**: PostgreSQL 12+
* **Message Queue**: RabbitMQ 3.8+ (必选，系统核心异步总线，用于支持海量数据采集与重试)

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

# 3. 初始化财务基础数据 (科目、费率、合约示例) (New)
python scripts/init_cost_codes.py
python scripts/init_labor_rates.py
python scripts/init_purchase_contracts.py
python scripts/init_revenue_contracts.py

### 2.5 服务台门户部署 (Service Desk Web Portal)
*   **资源部署**: 将 `devops_portal/static/` 目录下的所有 HTML/CSS/JS 文件部署至 Nginx 静态服务目录，或确保 FastAPI 应用已挂载静态目录。
*   **认证配置**: 确保环境变量中已配置 `SECURITY__SECRET_KEY` (用于 JWT 签名) 和有效期。
*   **通知服务**: 确保 RabbitMQ 服务运行正常，该组件负责支撑 SSE 实时推送功能。
```

## 3. 配置详解 (Configuration)

本项目采用 Pydantic Settings 管理配置，**所有配置均通过环境变量注入**。在 `.env` 文件中，嵌套配置使用 **双下划线 (`__`)** 作为分隔符。

### 核心配置清单

| 类别 | 环境变量 Key | 说明 | 示例 |
|:---|:---|:---|:---|
| **数据库** | `DATABASE__URI` | 数据库连接串 | `postgresql://user:pass@host:5432/db` |
| | `STORAGE__DATA_DIR` | 持久化数据目录 | `/app/data` |
| **GitLab** | `GITLAB__URL` | GitLab 实例地址 | `https://gitlab.company.com` |
| | `GITLAB__PRIVATE_TOKEN` | 具有 API 权限的 Token | `glpat-xxxxxxxx` |
| | `GITLAB__CLIENT_ID` | OAuth2 Client ID | - |
| | `GITLAB__CLIENT_SECRET` | OAuth2 Client Secret | - |
| **SonarQube** | `SONARQUBE__URL` | SonarQube 地址 | `https://sonar.company.com` |
| | `SONARQUBE__TOKEN` | 用户 Token | `squ_xxxxxxxx` |
| **Jenkins** | `JENKINS__URL` | Jenkins 地址 | `http://jenkins.company.com` |
| | `JENKINS__USER` | 用户名 | `admin` |
| | `JENKINS__TOKEN` | API Token | `11ea...` |
| **消息队列** | `RABBITMQ__HOST` | RabbitMQ 地址 | `rabbitmq` |
| | `RABBITMQ__QUEUE` | 队列名称 | `gitlab_tasks` |
| **AI 服务** | `AI__API_KEY` | LLM API Key | `sk-xxxx` |
| | `AI__BASE_URL` | LLM Base URL | `https://api.openai.com/v1` |
| **通知** | `NOTIFIERS__WECOM_WEBHOOK` | 企业微信 Webhook | `https://qyapi...` |

> **注意**: 如果使用 Docker Compose，请直接修改 `.env` 文件。如果使用 K8s，请创建 ConfigMap/Secret 并映射为环境变量。

## 4. 定时任务配置 (Scheduling)

建议使用 Crontab 进行任务调度。

```bash
# 编辑 crontab
crontab -e

# 每小时运行一次调度器，生成同步任务
0 * * * * cd /path/to/app && venv/bin/python -m devops_collector.scheduler >> logs/scheduler.log 2>&1

# 启动 Worker 进程 (生产环境建议使用 systemd 保持常驻)
# python -m devops_collector.worker
```

## 5. 常见问题排查 (Troubleshooting)

### Q: 初始化时报错 "FATAL: password authentication failed"

* **原因**: 数据库密码错误或 pg_hba.conf 未允许连接。
* **解决**: 检查 `.env` 中的 `DATABASE__URI` 或 `POSTGRES_PASSWORD` 配置，确保用户名密码正确且有建表权限。

### Q: GitLab 同步极慢或卡住

* **原因**: 某些项目 Commit 历史过长 (如 10w+)。
* **解决**:
    1. 检查日志查看卡在哪个 Project ID。
    2. 系统会自动记录断点，杀掉进程重启后会从断点处继续，不要为了速度频繁重启。
    3. 检查网络带宽。

### Q: SonarQube 数据为空

* **原因**: 项目 Key 匹配失败。
* **解决**:
  * 默认匹配规则是 `GitLab Path With Namespace` == `Sonar Project Key`。
  * 如果规则不同，需修改 `plugins/sonarqube/collector.py` 中的 `_resolve_project_key` 逻辑。

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

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
*   **认证配置**: 确保 `config.ini` 中 `[security]` 章节已配置 `secret_key` (用于 JWT 签名) 和 `token_expire_minutes`。
*   **通知服务**: 确保 RabbitMQ 服务运行正常，该组件负责支撑 SSE 实时推送功能。
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
| `enable_deep_analysis`| 是否开启深度分析模式 (Events, Diff, Wiki) | `true` |

### [sonarqube]

| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `url` | SonarQube 实例地址 | `https://sonar.company.com` |
| `token` | 用户 Token | `squ_xxxxxxxx` |

### [jenkins]

| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `url` | Jenkins 实例地址 | `http://jenkins.company.com` |
| `user` | Jenkins 用户名 | `admin` |
| `token` | API Token (用户设置 -> Configure 生成) | `11ea...` |

### [rabbitmq]

| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `host` | RabbitMQ 服务地址 | `localhost` 或 `rabbitmq` |
| `queue` | 任务队列名称 | `devops_tasks` |

### [common]

| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `org_name` | 顶层组织名称，用于报表标题 | `MyTechCorp` |
| `raw_data_retention_days` | 原始数据保留天数 (默认 30) | `30` |

### [enrichment] (New)

| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `ai_provider` | AI 服务商 (openai/azure/local) | `openai` |
| `api_key` | API Key | `sk-xxxx` |
| `model_name` | 使用的模型名称 | `gpt-4o-mini` |
| `enable_ai_qa` | 是否开启 AI 自动化测试生成 | `true` |

### [notifiers] (New)

| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `wecom_webhook` | 企业微信 Webhook | `https://qyapi.weixin.qq.com/...` |
| `feishu_webhook` | 飞书 Webhook | `https://open.feishu.cn/...` |
| `dingtalk_webhook`| 钉钉 Webhook | `https://oapi.dingtalk.com/...` |

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
* **解决**: 检查 `config.ini` 中的数据库 URL，确保用户名密码正确且有建表权限。

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

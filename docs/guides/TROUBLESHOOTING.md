# 故障排查指南 (Troubleshooting Guide)

**版本**: 4.1.0
**日期**: 2026-01-11

本文档汇总了 DevOps Data Application Platform 常见问题及其解决方案。

---

## 目录

1. [部署与启动问题](#1-部署与启动问题)
2. [数据库问题](#2-数据库问题)
3. [数据同步问题](#3-数据同步问题)
4. [认证与授权问题](#4-认证与授权问题)
5. [Dashboard 问题](#5-dashboard-问题)
6. [Docker 容器问题](#6-docker-容器问题)
7. [性能问题](#7-性能问题)
8. [日志与调试](#8-日志与调试)

---

## 1. 部署与启动问题

### Q1.1: 执行 `make deploy` 时报错 "Cannot connect to Docker daemon"

**症状**:

```text
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**原因**: Docker 服务未启动或当前用户无权限访问 Docker。

**解决方案**:

```bash
# 1. 检查 Docker 服务状态
sudo systemctl status docker

# 2. 启动 Docker 服务
sudo systemctl start docker

# 3. 将当前用户加入 docker 组（需重新登录生效）
sudo usermod -aG docker $USER
```

---

### Q1.2: 镜像拉取超时或失败

**症状**:

```text
Error response from daemon: Get "https://registry-1.docker.io/v2/": net/http: request canceled
```

**原因**: 网络问题或 Docker Hub 被墙。

**解决方案**:

```bash
# 使用项目提供的镜像加速脚本（中国大陆用户）
sudo bash scripts/setup_china_mirrors.sh

# 或手动配置 daemon.json
cat > /etc/docker/daemon.json << EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
EOF
sudo systemctl restart docker
```

---

### Q1.3: 端口被占用

**症状**:

```text
Error starting userland proxy: listen tcp4 0.0.0.0:8000: bind: address already in use
```

**解决方案**:

```bash
# 查找占用端口的进程
# Linux
sudo lsof -i :8000

# Windows
netstat -ano | findstr :8000

# 终止进程或修改 docker-compose.yml 中的端口映射
```

---

## 2. 数据库问题

### Q2.1: 初始化报错 "password authentication failed"

**症状**:

```text
FATAL: password authentication failed for user "postgres"
```

**原因**: `.env` 中的数据库密码与实际不匹配。

**解决方案**:

```bash
# 1. 检查 .env 文件中的密码配置
cat .env | grep -E "POSTGRES_PASSWORD|DATABASE__URI"

# 2. 确保 docker-compose.yml 中的环境变量一致

# 3. 如果是首次部署，需删除旧数据卷重新初始化
docker-compose down -v
docker-compose up -d
```

---

### Q2.2: 数据库连接超时

**症状**:

```text
OperationalError: could not translate host name "db" to address
```

**原因**: Docker 网络未正确建立或数据库容器未启动。

**解决方案**:

```bash
# 1. 检查数据库容器状态
docker-compose ps db

# 2. 查看数据库日志
docker-compose logs db

# 3. 重启服务
docker-compose restart db
```

---

### Q2.3: 表或列不存在

**症状**:

```text
relation "xxx" does not exist
column "xxx" does not exist
```

**原因**: dbt 模型未运行或 Schema 不同步。

**解决方案**:

```bash
# 1. 运行 dbt 构建所有模型
make dbt-run

# 或手动进入容器执行
docker-compose exec api dbt run --project-dir dbt_project

# 2. 如果是 Legacy 视图，检查 SQL 文件
docker-compose exec -T db psql -U postgres -d devops_db -f /app/devops_collector/sql/XXX.sql
```

---

## 3. 数据同步问题

### Q3.1: GitLab 同步极慢或卡住

**症状**: 同步进度长时间不动，CPU/内存占用低。

**原因**: 某些项目 Commit 历史过长（如 10 万+条），或网络延迟高。

**解决方案**:

1. 查看日志确定卡在哪个 Project:

```bash
docker-compose logs -f api | grep -i "syncing project"
```

1. 系统支持**断点续传**，可安全重启:

```bash
docker-compose restart api
```

1. 跳过超大项目（在配置中排除）:

```python
# config.ini 中添加排除规则
[gitlab]
excluded_projects = project-with-huge-history
```

---

### Q3.2: SonarQube 数据为空

**症状**: Dashboard 中 SonarQube 相关指标全部为空。

**原因**: 项目 Key 匹配失败。

**解决方案**:

1. 默认匹配规则:

```text
GitLab Path With Namespace == Sonar Project Key
例如: group/project-name
```

1. 验证 SonarQube 连接:

```bash
curl -u "TOKEN:" "https://sonar.example.com/api/projects/search"
```

1. 如果命名规则不同，需修改匹配逻辑:

```python
# plugins/sonarqube/collector.py
# 修改 _resolve_project_key() 方法
```

---

### Q3.3: RabbitMQ 队列积压

**症状**: 任务未执行，队列消息持续增长。

**解决方案**:

```bash
# 1. 检查 Worker 状态
docker-compose logs worker

# 2. 查看队列状态（访问 RabbitMQ 管理界面）
# http://localhost:15672 (guest/guest)

# 3. 重启 Worker
docker-compose restart worker

# 4. 清空积压队列（谨慎操作）
docker-compose exec rabbitmq rabbitmqctl purge_queue gitlab_tasks
```

---

## 4. 认证与授权问题

### Q4.1: GitLab OAuth 回调失败

**症状**:

```text
The redirect_uri is missing or invalid
```

**原因**: GitLab OAuth 配置的回调地址不匹配。

**解决方案**:

1. 检查 GitLab OAuth Application 配置:
   - Redirect URI 必须精确匹配
Format: `http://localhost:8000/callback`

2. 检查 `.env` 配置:

```bash
GITLAB__CLIENT_ID=your_client_id
GITLAB__CLIENT_SECRET=your_client_secret
GITLAB__REDIRECT_URI=http://localhost:8000/callback
```

---

### Q4.2: JWT Token 过期

**症状**:

```text
401 Unauthorized: Token has expired
```

**解决方案**:

```bash
# 1. 客户端重新登录获取新 Token

# 2. 调整 Token 有效期（可选）
# .env 中配置
JWT_EXPIRATION_HOURS=48
```

---

### Q4.3: 用户无权限访问资源

**症状**:

```text
403 Forbidden: Access denied
```

**解决方案**:

1. 检查用户角色:

```sql
SELECT u.email, r.name as role
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE u.email = 'user@example.com';
```

1. 分配正确角色:

```sql
INSERT INTO user_roles (user_id, role_id) VALUES (user_id, role_id);
```

---

## 5. Dashboard 问题

### Q5.1: Streamlit 页面加载报错

**症状**: Dashboard 页面显示红色错误框。

**解决方案**:

```bash
# 1. 查看详细错误信息
docker-compose logs dashboard

# 2. 检查 SQL 查询是否有问题
# 确保所有表都有 public_marts 前缀

# 3. 运行 Dashboard 测试脚本
python scripts/test_dashboard_pages.py
```

---

### Q5.2: 图表数据不显示

**症状**: 页面加载成功但图表空白。

**原因**: 数据库中无数据或查询条件不匹配。

**解决方案**:

```bash
# 1. 验证数据是否存在
docker-compose exec db psql -U postgres -d devops_db -c "SELECT COUNT(*) FROM public_marts.xxx;"

# 2. 检查时间范围筛选条件

# 3. 确认 dbt 模型已构建
make dbt-run
```

---

## 6. Docker 容器问题

### Q6.1: 容器频繁重启

**症状**: `docker-compose ps` 显示 Restarting 状态。

**解决方案**:

```bash
# 1. 查看重启原因
docker-compose logs --tail=100 <service_name>

# 2. 常见原因:
# - 内存不足 (OOM Killed)
# - 启动命令错误
# - 依赖服务未就绪

# 3. 增加内存限制
# docker-compose.yml 中调整 mem_limit
```

---

### Q6.2: 磁盘空间不足

**症状**:

```text
no space left on device
```

**解决方案**:

```bash
# 1. 清理未使用的 Docker 资源
docker system prune -a

# 2. 清理旧日志
docker-compose logs --no-log-prefix > /dev/null

# 3. 检查数据卷大小
docker system df
```

---

## 7. 性能问题

### Q7.1: API 响应缓慢

**可能原因及解决方案**:

| 原因 | 诊断方法 | 解决方案 |
| :--- | :--- | :--- |
| 数据库慢查询 | 查看 PostgreSQL 慢日志 | 添加索引或优化 SQL |
| 内存不足 | `docker stats` | 增加容器内存限制 |
| 网络延迟 | 检查容器间网络 | 使用 Docker 内部网络 |

### Q7.2: dbt 构建时间过长

**解决方案**:

```bash
# 1. 仅构建变更模型
dbt run --select state:modified+ --state ./target

# 2. 增量构建
dbt run --select tag:incremental

# 3. 并行构建
dbt run --threads 4
```

---

## 8. 日志与调试

### 8.1 日志位置

| 服务 | 日志获取方式 |
| :--- | :--- |
| API | `docker-compose logs api` |
| Worker | `docker-compose logs worker` |
| Database | `docker-compose logs db` |
| Dashboard | `docker-compose logs dashboard` |

### 8.2 调试模式

```bash
# 启用 Debug 模式
# .env 中设置
DEBUG=true
LOG_LEVEL=DEBUG

# 重启服务生效
docker-compose restart api
```

### 8.3 常用调试命令

```bash
# 进入容器 Shell
docker-compose exec api bash

# 测试数据库连接
docker-compose exec api python -c "from devops_collector.core.db import get_engine; print(get_engine().connect())"

# 测试 GitLab API
docker-compose exec api python -c "from devops_collector.plugins.gitlab.client import GitLabClient; print(GitLabClient().test_connection())"
```

---

## 需要更多帮助?

如果以上方案未能解决您的问题，请:

1. 检查项目 [Issue 列表](https://gitlab.example.com/devops/devops_collector/issues) 是否有类似问题
2. 收集以下信息后提交新 Issue:
   - 系统版本 (`cat /etc/os-release`)
   - Docker 版本 (`docker --version`)
   - 完整错误日志
   - 复现步骤

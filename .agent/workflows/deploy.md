---
description: [deploy] 生产发布与核对工作流 — 包含备份、灰度部署与健康探针校验
---

# 生产发布与核对工作流 (Deployment Workflow)

> **触发时机**：任务已通过 `/merge` 准入测试，准备部署至生产环境或生产环境演练。
> **核心准则**：部署必须可观测、可回滚、有证据。

---

## Step 1: 发布前快照 (Pre-deployment Snapshot)

1. **数据库静默备份**：
   ```powershell
   make db-backup  # 备份 devops_db 至 artifacts/backups/
   ```
2. **环境变量校验**：检查生产环境 `.env` 的敏感密钥是否存在缺失（对比 `.env.example`）。

## Step 2: 灰度部署执行 (Execution)

1. **分支验证**：确保当前处于 `main` 或 `release/*` 分支。
2. **容器滚动更新**：
   ```powershell
   make deploy-prod
   ```
   - **注意事项**：由于使用 Docker Compose，确保 `restart: unless-stopped` 已生效。

## Step 3: 金丝雀健康探针 (Liveness Check)

部署后 AI 必须执行以下探针，确认系统未处于“假死”状态：

1. **核心 API 探针**：调用 `GET /health` 或 `/api/v1/auth/status`，确保返回 `200 OK`。
2. **Worker 队列探测**：
   ```bash
   docker-compose exec rabbitmq rabbitmqctl list_queues
   ```
   - 检查是否有积压，消费者是否在线。
3. **日志金丝雀审计**：
   ```bash
   docker-compose logs -f --tail=50 api worker
   ```
   - 扫描前 5 分钟日志，确认为 `INFO/DEBUG` 等级，无爆发性 `ERROR/CRITICAL`。

---

## Step 4: 发布存证与发布说明 (Post-deploy)

1. 更新 `progress.txt` 将对应任务标记为 `[Deployed] @TIMESTAMP`。
2. 生成 3 行发布说明 (Release Notes)：
   - `🚀 新功能: ...`
   - `🔧 修复项: ...`
   - `⚠️ 运维注意: ...`

---

## 完工签章

在回复中包含：
```
[Production Deployed] Version: [Tag] | Health: All Green | Backup: artifacts/backups/xxx.sql
```

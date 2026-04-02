---
description: 回滚预案模板 — 针对不同变更类型的应急恢复操作清单
---

# 回滚预案 (Rollback Playbook)

> **适用场景**：L3/L4 级任务中涉及破坏性变更时，必须在实施前填写本预案。
> **核心原则**：每个变更都必须有"如何退回去"的答案。

---

## Step 0: 预演与快照 (Dry-run - L4 Only)

针对 L4 (架构级) 涉及核心 `mdm_*` 表的变更，必须在实施前：
1. **本地回滚演练**：在临时分支模拟执行 `alembic upgrade` 后立即 `alembic downgrade`，验证其语义原子性。
2. **数据快照对齐**：确保 SCD2 字段 (valid_from/to) 的回滚不产生逻辑重叠。

## Step 1: 变更分类与回滚策略

根据变更类型选择对应的回滚模板：

### 🗄️ 类型 A: 数据库 Schema 变更 (Alembic Migration)

**实施前**：
```bash
# 记录当前 Alembic 版本
docker-compose exec api alembic current
# 创建 Git Tag 作为安全锚点
git tag pre-migration-<ticket-id>
```

**回滚操作**：
```bash
# 降级一个版本
docker-compose exec api alembic downgrade -1
# 若需要回到特定版本
docker-compose exec api alembic downgrade <revision_id>
```

**验证**：
```bash
docker-compose exec db psql -U postgres -d devops_db -c "\dt"
docker-compose exec api alembic current
```

**注意事项**：
- 每个 Migration 必须实现 `downgrade()` 方法。
- 包含 `DROP TABLE`/`DROP COLUMN` 的操作必须先执行物理快照备份。
- Schema 变更严禁与应用代码变更同时发布。
- **数据一致性校验 [MANDATORY]**：回滚时严禁手动通过 `DELETE FROM` 删除 SCD2 快照行，必须遵循 Alembic 提供的回退脚本，确保 `version_id` 与审计字段的一致性。
- **技术卡点：mdm_* 核心表审计 [MANDATORY]**：
    - **强制动作**：若任务涉及 `mdm_*` 表变更，AI 必须显式重读 [`contexts.md#13`](contexts.md#L406) (数据库兼容策略)。
    - **无损回滚自问答**：“如果此版本发布失败，当前数据库 Schema 是否能在不丢失生产数据的情况下通过 `alembic downgrade` 回退？”
    - **兼容律校验**：是否严格遵循“先增列 (Nullable)、后迁数据、最后删旧列”的顺序？**严禁**直接将旧列重命名或物理删除作为单一 Migration。

---

### 🐰 类型 B: 消息拓扑变更 (RabbitMQ)

**实施前**：
```bash
# 导出当前队列配置 (通过 Management API)
docker-compose exec rabbitmq rabbitmqctl list_queues name messages consumers
```

**回滚操作**：
```bash
# 重新声明旧队列（RabbitMQ 队列声明是幂等的）
# 回退代码并重启 Worker
git checkout pre-mq-change -- devops_collector/core/message_queue.py
docker-compose restart worker
```

**验证**：
```bash
docker-compose exec rabbitmq rabbitmqctl list_queues name messages consumers
docker-compose logs --tail=20 worker
```

---

### ⚙️ 类型 C: 配置/环境变量变更

**实施前**：
```bash
# 备份当前 .env
copy .env .env.backup.<date>
```

**回滚操作**：
```bash
# 恢复备份
copy .env.backup.<date> .env
docker-compose up -d
```

---

### 📦 类型 D: 代码逻辑变更 (Git Revert)

**回滚操作**：
```bash
# 撤销最近一次合并提交
git revert HEAD --no-edit
git push origin main

# 或回到指定的安全 Tag
git reset --hard pre-<feature>-tag
git push origin main --force  # ⚠️ 需用户确认
```

---

## Step 2: 预案模板 (填写在 Task Brief 的 ⚠️ 风险 部分)

```
📛 回滚预案:
- 变更类型: [A/B/C/D]
- 安全锚点: [Git Tag / Alembic Revision / .env Backup]
- 回滚命令: [具体命令]
- 回滚验证: [如何确认已成功回退]
- 预计回滚耗时: [Xmin]
- 数据影响: [是否有不可逆的数据变更？如有，备份方案是什么？]
- **Schema 兼容性声明**: [符合 contexts.md#13 向后兼容策略 / 或不符合，原因及补救：]
```

---

## 关键红线

- ❌ **严禁**在没有回滚预案的情况下执行 DB Migration
- ❌ **严禁**在 `mdm_*` 核心表变更中执行破坏性的非兼容性操作（如直接物理删除字段）
- ❌ **严禁** `DROP TABLE`/`DROP COLUMN` 而没有独立的数据快照备份
- ❌ **严禁**强制推送 (`--force`) 到 main 而没有用户明确授权
- ✅ 每次破坏性变更前必须创建 Git Tag 作为安全锚点

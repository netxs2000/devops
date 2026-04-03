# Spike 结论报告: 系统审计日志集成与溯源追踪 [MANDATORY TAG: [Spike-Result]]

- **日期**: 2026-04-03
- **耗时**: 2.5h / 时间盒 4h
- **结论**: 🟢 Go (方案高度可行)

## ⚖️ 选型对比

| 方案 | 追踪粒度 | 性能损耗 | 适用场景 |
| :--- | :---: | :---: | :--- |
| **A: 业务层埋点** | 逻辑级 (Logic) | 极高 (侵入式代码) | 仅针对极个别关键接口 (如 提款/删库) |
| **B: MySQL BINLOG** | 物理级 (Physical) | 极低 (无业务影响) | 适用于全量异构同步，难以溯源至 API 身份 |
| **C: SQLAlchemy Listeners** | **实体级 (Entity)** | **低 (异步解构)** | **推荐方案**：能获取字段变更 Diff，且能通过 ContextVar 关联用户身份 |

## 📐 探针验证架构 (The V-Gate Architecture)

1. **Identity Capture (FastAPI)**: 在 `AuditMiddleware` 中捕获 `User-Agent`, `IP` 和 `UserID` 并注入 `ContextVars`。
2. **Global Broadcast (ContextVars)**: 提供线程/协程隔离的身份“广播站”，供 DB 层随时调阅。
3. **Change Tracking (SQLAlchemy)**: 绑定 `after_update` 钩子，通过 `inspect(target).attrs.history` 自动提取字段变更快照。

## 🛡️ 等保三级 (MLPS L3) 合规映射
- **身份鉴别 [S3]**: 已通过中间件实现“每项关键操作均关联至唯一身份”。
- **安全审计 [S3]**: 覆盖了“由于各种原因导致的数据库非授权修改”，审计日志包含 Who, When, What, Result 四要素。

## 💡 下一步建议 (Next Steps)
- 建议初始化 `audit_logs` 模型表，并发起 **L2 级任务** 实施。
- **阻断策略**：生产环境必须将审计日志异步写入（推荐 Kafka/Logstash），防止因审计表 DB 压力导致业务阻塞。

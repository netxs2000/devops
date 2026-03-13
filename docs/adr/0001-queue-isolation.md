# ADR 0001: 消息队列物理隔离 (Queue Isolation)

## 状态 (Status)
已通过 (Accepted)

## 上下文 (Context)
DevOps 平台集成了多个数据源（如 GitLab, ZenTao, SonarQube）。
* **GitLab**: 拥有 1000+ 项目，同步任务频率极高，产生大量短任务。
* **ZenTao**: 项目数相对较少（100+），但同步逻辑复杂，单次任务价值高且时效性敏感。

如果所有任务共享同一个 RabbitMQ 队列，高频数据源（GitLab）会产生“洪泛效应 (Flood)”，导致低频但关键的数据源任务在队列中长时间排队，产生“饥饿效应 (Starvation)”。

## 决策 (Decision)
1. **物理隔离**: 为每个数据源插件创建独立的 RabbitMQ 队列。
2. **命名公约**: 队列名称统一为 `{source}_tasks`（如 `gitlab_tasks`, `zentao_tasks`）。
3. **动态路由**: `MessageQueue.publish_task()` 根据 Payload 中的 `source` 字段自动分发到对应队列。
4. **SSOT (单一事实来源)**: 队列名称由 `PluginRegistry` 动态生成，严禁在各模块硬编码。
5. **公平消费**: Worker 进程使用 `prefetch_count=1` 并同时监听所有已注册队列，确保各源获得公平的处理时间片。

## 后果 (Consequences)
* **优点**: 彻底解决数据源间的“饥饿”问题；支持针对特定源单独水平扩容 Worker。
* **缺点**: 略微增加了运维监控的复杂度（需监控多个队列深度）。
* **风险**: 若新增插件忘记在 Registry 注册，可能会导致任务无法正确入队。

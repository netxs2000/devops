# ADR 0002: 跨源关联标识符类型归一化 (Identifier Type Normalization)

## 状态 (Status)
已通过 (Accepted)

## 上下文 (Context)
平台涉及多源异构数据关联：
* **GitLab**: 内部 ID 为整型 (Integer)。
* **ZenTao**: 内部 ID 存在多种混合模式 (String 或 Integer)。
* **MDM**: 主项目 ID 和主身份 ID 定义为字符串 (Varchar)。

在 Postgres/dbt 执行 `JOIN` 操作时，如果类型不一致（如 `Integer = Character Varying`），会触发 `operator does not exist` 错误并中断构建。

## 决策 (Decision)
1. **类型对齐**: 在 dbt 的语义层（Intermediate 及以上），所有跨源关联的业务主键（Master IDs / Entity IDs）强制统一为 **字符串 (String)** 类型。
2. **Staging 转换**: 所有的 Staging 模型在输出 ID 时，若源端为数值，必须显式执行 `::text` 转换。
3. **桥接模型**: 跨系统 ID 的关联（如 GitLab ID 到 Master Project ID）必须且仅能通过 `int_project_resource_map` 进行路由，严禁在 FCT 层进行非标的硬链接。

## 后果 (Consequences)
* **优点**: 保证了全链路数据关联的稳定性，消除了常见的 SQL 编译异常。
* **缺点**: 在联表查询时相比纯整型 Join 有极细微的性能损耗（在当前百万级数据量级下可忽略）。
* **风险**: 开发者如果不查看 Staging 定义，可能在下游误用原始数值 ID 导致类型冲突。

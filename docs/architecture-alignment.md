# DevOps Platform Architecture Alignment & MDM Guidelines

## 1. 核心模型准则 (Core Model Principles)

### 1.1 代理主键 (Surrogate PK)
- **强制约束**: 所有业务核心模型 (`Organization`, `Product`, `ProjectMaster`) 必须使用整数自增主键 `id` (PK)。由于 User 涉及跨系统、跨实例的身份合并，使用 UUID（而非自增 ID）能更有效地防止 ID 碰撞。因此，`User`为特例 (Exception)。
- **外部外键 (FK)**: 跨表关联必须使用代理主键 `id`。禁止直接关联 `project_code` 或 `product_code` 等业务主键指标。
- **业务主键 (Natural Key)**: 业务主键 (`product_code`, `project_code`) 仅作为业务侧的唯一索引名及 UI 层面的展示 ID。

### 1.2 SCD Type 2 (缓慢变化维)
- **版本化策略**: 使用 `is_current` (Boolean) 指向当前活跃记录。
- **审计追踪**: 包含 `created_at`, `updated_at`, `effective_date`, `expiration_date`。
- **引用一致性**: 外键关联到 `id` 某一个具体版本。如需查询最新的业务关联视图，应通过 `is_current` 过滤。

## 2. 身份识别与对齐 (Identity Alignment)

### 2.1 全局用户中心 (Global User Center)
- **SSOT (Single Source of Truth)**: `User` 模型是全局唯一的人员主数据。字段名统一为 `primary_email` (而非 `email`)。
- **全局 ID**: `global_user_id` (UUID) 是人员在系统内的逻辑唯一标识。

### 2.2 身份映射 (Identity Mapping)
- **协议**: `IdentityMapping` 负责将外部系统 ID (`external_user_id`) 路由到 `global_user_id`。
- **自动对齐规则**: `Email (Lower Case) > Employee_ID > Name (Fuzzy)`.

## 3. 数据同步流水线 (Data Sync Pipeline)

### 3.1 暂存区隔离 (Staging Area Isolation) [DECISION]
- **Worker 职责**: 插件 Worker (GitLab, ZenTao) **禁止**直接创建或修改 MDM 核心实体的外键关联逻辑。
- **隔离模式**: Worker 仅将源系统数据（含源系统 ID）写入各自插件的 `Staging` 表。
- **转正逻辑 (Promotion)**: 由核心层的 `Service` 或 `Task` 负责读取 Staging 数据，调用 `MDM_Resolver` 将源 ID 解析为内部 `id`，并执行最终入库。

## 4. 开发与测试规范 (Development & QA)

### 4.1 测试一致性
- **内存化**: 单元测试必须使用 `:memory:` 模式，以确保极致的执行速度。
- **全量发现**: 测试启动前必须 import `devops_collector.models` 包，以确保 SQLAlchemy 能够发现所有插件定义的模型。

### 4.2 错误处理
- **严禁吞嗜**: 所有业务逻辑捕获异常必须使用 `except Exception:` 并在日志中记录 Context。
- **透明解析**: 涉及 ID 转换的代码必须包含 `None` 值降级处理，避免链式调用崩溃。

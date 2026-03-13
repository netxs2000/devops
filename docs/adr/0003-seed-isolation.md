# ADR 0003: 种子数据与原始采集表的物理隔离 (Seed-Source Isolation)

## 状态 (Status)
已通过 (Accepted)

## 上下文 (Context)
项目中存在部分基础数据既通过 dbt Seed 加载，又通过插件从源端（如 LDAP/HR）同步：
* **案例**: `ldap_accounts` 同时作为 `.csv` 种子和 `raw` 模式下的原始表存在。
* **冲突**: 当执行 `dbt build --full-refresh` 时，dbt 加载种子会执行 `DROP TABLE CASCADE`。由于 Postgres 的级联机制，依赖该同名表的下游 Staging 视图会被同步物理删除，导致后续模型构建因“关系不存在”而失败。

## 决策 (Decision)
1. **命名隔离**: 所有的 dbt 种子文件（Seed Files）必须强制增加 `seed_` 前缀（例如：`seed_ldap_accounts.csv`）。
2. **引用规范**: 
    - Staging 模型关联第三方原始表时，必须使用 `{{ source('raw', '...') }}`。
    - Staging 关联手动维护的种子时，必须使用 `{{ ref('seed_...') }}`。
3. **职责分离**: 坚决避免同一业务实体在同一模式下同时存在 Seed 和 Source。

## 后果 (Consequences)
* **优点**: 解决了全量刷新构建时的连锁删除崩溃问题，提升了流水线的鲁棒性。
* **缺点**: 现有的 Staging 代码需要一次性迁移和重构。
* **风险**: 新开发者若不遵循前缀公约，仍可能引入新的冲突。

# 数据完整性验证指南

## 概述

本文档描述了如何验证 DevOps 效能平台采集的数据的**完整性**和**准确性**。数据质量是平台价值的基石,任何指标计算的前提都是数据本身的可信度。

## 验证维度

### 1. 数据完整性 (Completeness)

**目标**: 确保"不漏"  
**方法**: 对比 GitLab API 返回的资源总数与数据库中的记录数

验证对象:
- Issues (议题)
- Merge Requests (合并请求)
- Pipelines (流水线)
- Commits (提交记录)

**判定标准**:
- ✅ **完全匹配**: DB 数量 = API 数量
- ⚠️ **轻微偏差**: 差异 < 5% (可能由于同步时间差)
- ❌ **严重偏差**: 差异 ≥ 5% (需要重新同步)

### 2. 业务逻辑准确性 (Business Logic Accuracy)

**目标**: 确保"不算错"  
**方法**: 抽样验证关键指标的计算逻辑

重点验证对象:
- **MR 评审轮次 (review_cycles)**: 验证是否准确捕捉了所有评审交互
- **Issue 周期时间 (Cycle Time)**: 验证状态流转时间计算的准确性
- **阻塞时间 (Blockage Time)**: 验证阻塞事件的起止时间是否闭环

**判定标准**:
- ✅ **逻辑一致**: 计算结果与 API 原始数据推导结果一致
- ⚠️ **需人工核对**: 存在边界情况,需要业务专家判断
- ❌ **逻辑错误**: 计算结果明显不符合业务规则

### 3. 字段级准确性 (Field-Level Accuracy)

**目标**: 确保"不错"  
**方法**: 随机抽样,逐字段比对 API 原始响应与数据库记录

验证字段:
- 标题 (Title)
- 状态 (State)
- 时间戳 (created_at, updated_at, merged_at)
- 作者信息 (Author)

**判定标准**:
- ✅ **字段匹配**: 所有抽样记录的关键字段完全一致
- ❌ **字段不匹配**: 存在字段值差异 (需排查转换逻辑)

## 使用方法

### 前置条件

1. 确保数据库连接配置正确 (`config.ini`)
2. 确保 GitLab API Token 有效
3. 项目已至少完成一次完整同步

### 运行验证脚本

```bash
# 基础验证 (验证指定项目的数据完整性)
python scripts/verify_data_integrity.py --project-id <PROJECT_ID>

# 指定抽样数量 (默认为 5)
python scripts/verify_data_integrity.py --project-id <PROJECT_ID> --sample-size 10
```

### 输出示例

```
2025-12-26 23:45:00 - DataVerifier - INFO - Starting verification for Project: my-project (ID: 123)
2025-12-26 23:45:01 - DataVerifier - INFO - --- Verify 1: Data Completeness (Counts) ---
2025-12-26 23:45:02 - DataVerifier - INFO - ✅ Issues: Match (45)
2025-12-26 23:45:03 - DataVerifier - ERROR - ❌ Merge Requests: Mismatch! DB=38, API=42, Diff=4 (9.5%)
2025-12-26 23:45:04 - DataVerifier - INFO - ✅ Pipelines: Match (156)
2025-12-26 23:45:05 - DataVerifier - INFO - --- Verify 2: Logic Check (MR Review Cycles) [Sample: 5] ---
2025-12-26 23:45:06 - DataVerifier - INFO - MR !12: DB Cycles=3 | API Notes=5 | OK
2025-12-26 23:45:07 - DataVerifier - WARN - MR !34: Found 8 discussion notes but review_cycles is 0
```

## 验证结果解读

### 完整性不匹配的常见原因

1. **同步未完成**: 数据采集任务仍在进行中
2. **增量同步遗漏**: `since` 参数设置不当,导致部分数据未被拉取
3. **API 分页问题**: 分页逻辑存在 Bug,导致某些页的数据被跳过
4. **权限问题**: Token 权限不足,无法访问某些私有 Issue/MR

### 逻辑准确性异常的常见原因

1. **事件解析错误**: GitLab API 返回的事件结构发生变化
2. **时区处理问题**: 时间戳转换时未正确处理时区
3. **边界条件未覆盖**: 例如 MR 被关闭后又重新打开的情况

## 修复建议

### 数据完整性问题

```bash
# 1. 重新触发全量同步
python -m devops_collector.worker --project-id <PROJECT_ID> --full-sync

# 2. 检查同步日志
SELECT * FROM sync_logs WHERE project_id = <PROJECT_ID> ORDER BY created_at DESC LIMIT 10;

# 3. 验证 API 连接
python scripts/verify_imports.py
```

### 逻辑准确性问题

1. **查看原始数据**: 检查 `raw_data_staging` 表中的 JSON payload
2. **对比 API 响应**: 使用 GraphQL Explorer 手动查询对比
3. **审查算法逻辑**: 检查 `devops_collector/core/algorithms.py` 中的计算逻辑

## 定期验证建议

### 验证频率

- **每日验证**: 对核心项目进行快速完整性检查
- **每周验证**: 对所有项目进行抽样逻辑验证
- **版本升级后**: 对所有维度进行全面验证

### 自动化集成

可以将验证脚本集成到 CI/CD 流程中:

```yaml
# .gitlab-ci.yml 示例
data_verification:
  stage: test
  script:
    - python scripts/verify_data_integrity.py --project-id $CI_PROJECT_ID
  only:
    - schedules
```

## 扩展验证项

未来可以增加的验证维度:

1. **时间序列一致性**: 验证 Commit 时间、MR 创建时间、Pipeline 触发时间的时序关系
2. **关联关系完整性**: 验证 MR 关联的 Commit SHA 是否在 Commits 表中存在
3. **指标计算验证**: 验证 DORA 四大指标的计算结果是否符合预期
4. **数据新鲜度**: 验证 `last_synced_at` 是否在合理时间范围内

## 故障排查清单

- [ ] 数据库连接是否正常
- [ ] GitLab API Token 是否有效
- [ ] 项目是否存在于数据库中
- [ ] 同步任务是否成功完成
- [ ] 是否有权限访问该项目的所有资源
- [ ] 网络连接是否稳定
- [ ] PostgreSQL 版本是否兼容 (推荐 12+)

## 相关文档

- [数据字典](../DATA_DICTIONARY.md)
- [数据治理策略](../DATA_GOVERNANCE.md)
- [同步策略说明](../DEPLOYMENT.md)
- [API 客户端文档](../devops_collector/plugins/gitlab/client.py)

---

**最后更新**: 2025-12-26  
**维护者**: DevOps Team

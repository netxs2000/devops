# 平台测试策略文档 (Test Strategy)

**发布版本**: v3.4.0  
**核心理念**: 宁可没有数据，不可有错数据。

## 1. 测试分层 (Testing Layers)

### 1.1 单元测试 (Unit Tests)
*   **目标**: 验证 Client 的 API 拼接逻辑、Utility 的转换函数。
*   **工具**: `pytest`, `unittest.mock`。
*   **覆盖要求**: 核心解析器（如 `DiffAnalyzer`）必须具备 100% 边界值覆盖。

### 1.2 全链路仿真测试 (Full-system Simulation) 🌟
*   **路径**: `tests/simulations/run_full_integration.py`
*   **逻辑**: 模拟 7 大系统（GitLab, Jira, Sonar, Jenkins, ZenTao, Nexus, JFrog）的完整 API 响应。
*   **关键验证项**: 
    *   **流水线追踪**: 验证 Jenkins Build 的 `commit_sha` 是否能精准关联到 GitLab 对应的提交记录。
    *   **身份扇出**: 验证修改 `IdentityMapping` 后，是否所有关联系统的 Activity 全部归并至同一 User 下。
    *   **依赖图谱**: 验证 `issuelinks` 导出的 `traceability_links` 是否能正确呈现跨项目阻塞逻辑。

### 1.3 数据重播验证 (Data Replay & Reprocessing)
*   **脚本**: `scripts/reprocess_staging_data.py`
*   **验证流程**:
    1.  清空事实表 (Fact Tables)。
    2.  保持 `raw_data_staging` 原始数据不变。
    3.  修改 Transform 映射逻辑（如调整 `ai_category` 判定准则）。
    4.  运行重播脚本。
    5.  校验事实表中的分类是否符合新准则。

## 2. 专项测试场景 (Special Scenarios)

### 2.1 容错与重试 (Fault Tolerance)
*   模拟 API 429 (Rate Limit) 响应，验证 Worker 是否正确执行指数退避。
*   模拟 API 500 错误，验证任务是否正确放回 RabbitMQ 延迟队列。

### 2.2 幂等性校验 (Idempotency)
*   重复运行 `sync` 任务，验证数据库中是否产生重复记录。系统要求必须使用 `Upsert` 策略。

### 2.3 性能压力
*   模拟 10 万级 Commit 的同步，验证 `Generator` 和 `Batch Commit` 机制下内存占用是否保持在 500MB 以下。

## 3. 验收指南 (Acceptance Criteria)

任何发布版本必须通过以下“三道关卡”：
1.  **静默期**: 在沙箱环境运行全量同步任务，且无 ERROR 日志。
2.  **数据穿透**: 随机抽取 5 个项目，手动核对页面指标与看板指标是否一致。
3.  **多端推送**: 确认异常告警能正确触达飞书/企微/钉钉机器人。

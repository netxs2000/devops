# 集团研发主数据系统技术架构设计

## 1. 逻辑架构 (Layered Architecture)



* **L1 (Staging/Bronze)**: 原始 API 镜像，存储 JSONB 格式。
* **L2 (Intermediate/Silver)**: **MDM 核心层**。执行清洗、脱敏、ID 归一化。
* **L3 (Marts/Gold)**: 业务聚合层。产出 DORA 指标宽表、项目财务月报。

## 2. 核心技术实现

### 2.1 身份归一算法 (Identity Mapping)
采用“权重累加法”识别同一自然人：
1.  **Level 1 (Weight 100)**: 企业邮箱精确匹配。
2.  **Level 2 (Weight 80)**: LDAP 账号映射。
3.  **Level 3 (Weight 40)**: 姓名+拼音模糊匹配（Levenshtein Distance）。
*系统自动合并评分 > 90 的账号，人工审核 60-90 分之间的账号。*

### 2.2 事件驱动链路 (Event Mesh)
在原 Python Worker 基础上引入 Kafka 接收 Webhook：
* **场景**: GitLab 代码推送即刻触发 dbt 增量计算。
* **优势**: 核心看板延迟从 T+1 提升至 T+Minutes。

### 2.3 安全与权限 (Security)
* **行级过滤 (RLS)**: 存储层强制隔离部门数据。
* **数据契约**: 使用 dbt-expectations 强制校验字段非空与类型。
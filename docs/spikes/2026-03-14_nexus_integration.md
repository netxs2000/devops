---
status: Proposed
date: 2026-03-14
author: AI Architect
topic: Nexus Artifact Sync for DORA & FinOps
---

# Spike: Nexus 3.x OSS 元数据同步框架与 DevOps 平台追踪能力建设

## 1. 业务背景 (Background)
目前公司的 DevOps DORA 度量体系已经延伸至 GitLab (源码合并) 与 ZenTao (需求/缺陷解决)，但“实际软件交付点”位于构建流水线的尽头 —— **Nexus OSS 3.69 私服**。

业务现状痛点：
1. **交付终点盲区**：无法确定 GitLab 合并后的代码是“真正打包生成了可分发制品”，还是因为流水线错误（Jenkins/Runner）止步不前。
2. **“孤儿”资产累积**：`nexus_component_map.csv`（产品与制品归属关系）靠手动且不及时维护，导致存储空间存在大量无主 (Orphan) Java Maven Snapshots / Release 制品及 Docker Images。
3. **二元构建生态**：Java 项目为主，**80% 依赖经典 Jenkins，20% 属于 GitLab CI 转型期**。Nexus 需要能同时对接两条管线盖下的“数据指纹”。

本实施方案旨在设计一套最小可行架构，将 Nexus V3 API 同步纳入现有的 Python `devops_collector` 抽数引擎，并赋能 dbt 数据模型。

## 2. 架构设计与技术路径 (Technical Approach)

### A. 数据库建模 (DB Schema)
在 DevOps Collector (PostgreSQL) 新增以下 Staging 层模型：

```python
# devops_collector/plugins/nexus/models.py
class NexusComponent(Base, TimestampMixin, SCDMixin):
    __tablename__ = "nexus_components"
    id = Column(String(255), primary_key=True)               # e.g., 'd3j2k...' (Nexus v3 component id)
    repository = Column(String(100), index=True)             # e.g., 'maven-releases', 'docker-hosted'
    format = Column(String(50))                              # e.g., 'maven2', 'docker'
    group = Column(String(255), index=True)                  # e.g., 'com.company.biz'
    name = Column(String(255), index=True)                   # e.g., 'portal-api'
    version = Column(String(100))                            # e.g., '1.0.0-SNAPSHOT'
    
class NexusAsset(Base, TimestampMixin):
    __tablename__ = "nexus_assets"
    id = Column(String(255), primary_key=True)               # e.g., '3f1e...'
    component_id = Column(String(255), ForeignKey("nexus_components.id"))
    path = Column(String(500))                               # e.g., '/com/company/biz/portal/1.0.0/'
    file_size_bytes = Column(BigInteger)                     # FinOps 关键：文件大小
    uploader_ip = Column(String(100))
    created_at = Column(DateTime(timezone=True))             # 构建产出时间轴
    last_downloaded_at = Column(DateTime(timezone=True))     # FinOps 关键：下载活跃度
```

### B. CI/CD 打包“印章”埋点机制 (Traceability Tags - 强烈建议)
仅抓取 Nexus 不能解决血缘（Lineage）问题，因为 Nexus 列表上只有 JAR 包名字。必须推动一次**极小成本的 CI 脚本改造**！

无论是 `Jenkinsfile` 还是 `.gitlab-ci.yml`，在执行 Maven / Docker 构建前，必须将当前的 **Git Commit SHA** 和 **CI Agent 标识**通过环境变量注入到包的元数据中：
*   **对于 Maven 机制**：建议在执行 `mvn deploy` 前，自动生成一个与 JAR 同名的 `.properties` 文件或使用 Nexus 的 tag 接口，写入：
    *   `ci.commit_sha=${GIT_COMMIT}`
    *   `ci.pipeline_url=${BUILD_URL}` 
*   一旦 Nexus OSS 3.x 组件有了这些属性（或者在 `nexus_assets` 的 path 中留痕），平台就可以顺藤摸瓜：**Nexus 制品版本 -> (通过 SHA1) -> GitLab 代码提交 -> (通过 Commit Message 关联) -> ZenTao 需求/Bug**。这是实现 DORA “变更前置时间 (Lead Time for Changes)”从提交到最终发布的**最后一环**。

### C. 数据抓取策略 (Sync Strategy via Plugin)
*   **开发组件**：仿照 `devops_collector/plugins/gitlab`，新增 `nexus` 抓取插件。
*   **采集接口**：使用 Nexus OSS 3.x REST API (`/service/rest/v1/components?repository={repo_name}`)。
*   **全量与增量 (Time Fence)**：由于 Nexus 通常不提供按时间过滤的拉取参数，我们只能使用 Continuation Token 分页扫全库，并在 Worker 内存中比对 `created_at`。与 GitLab 类似，针对 `snapshots` 等高频发版库，可采用强制时间隔离网（如 `> 2024-01-01`）避免拉挂 API。

### D. dbt 模型升级 (dbt Marts & Orphan Detection)
*   **孤儿发现表 (`fct_nexus_orphan_assets.sql`)**：将 `stg_nexus_components` 与手工配置表 `seed_nexus_component_map` (CSV) 定期做 `LEFT JOIN`。凡是名字不在 CSV 里的 `(group, name)`，统一高亮到“运维大屏”，自动发送邮件催促负责人认领并补充 CSV，否则视为野包，并在超过 90 天未下载（`last_downloaded_at`）后列入“清理废弃清单”。
*   **FinOps 降本看板 (`marts_nexus_storage_costs`)**：聚合 `file_size_bytes`，并在 dbt 中按团队进行归核结算：`“研发三组 Maven 库占用 1.5TB，其中 80% 是过期 180 天的 snapshot，预计月存储耗资 X 元。”`

## 3. 实施路径推荐 (Implementation Roadmap)

1. **第一阶段 (Step 1): 构建孤儿猎手与 FinOps 账本 (预计 3 天)**
    *   **开发 `nexus/client.py` 和 `worker.py`**：调用 Nexus OSS 3.x 扫描核心大类 Repo。
    *   **dbt `fct_nexus_orphan_assets`**：通过正则匹配对比手工 CSV，将遗漏登记的项目直接在 Grafana 报表曝光，倒逼研发团队完善元数据。这个功能**不需要改任何 Jenkins 流程**即可立刻见效。
2. **第二阶段 (Step 2): DORA 深度追溯 (预计 1 周)**
    *   在 Jenkins (80%) 的共享库 (Shared Library) 和 GitLab CI (20%) 的通用 Pipeline 模版中植入 **CI 元数据标签 (`GIT_COMMIT`) 自动注入脚本**。
    *   扩展 DevOps 收数脚本抓取这部分印章。
3. **第三阶段 (Step 3): 发布门禁与清理 (进阶)**
    *   打通 ZenTao 发布机制：禅道点击“发布”时拦截核对 Nexus 包是否存在。
    *   将 dbt 的 `fct_nexus_orphan_assets` 生成自动化删除脚本 (Nexus 垃圾回收器)，对无主且超期 180 天的文件进行硬删除释放资源空间。

# Spike: 企业微信 (WeCom) 主数据集成探针

## 1. 探针目标 (Spike Goal)
在 `devops_collector/plugins/wecom/` 目录下构建企业微信数据采集器插件，验证其是否能完美接入刚才我们加固的 **“异步对齐”**、**“数据血缘”** 以及 **“SCD Type 2”** 等 MDM 六大金科玉律。

## 2. 时间盒约束 (Timebox)
- **预估**: 4-6 小时 (设计 + Client 开发 + Worker 开发 + 联调)
- **Go / No-Go 标准**:
  - `Go`: 能够拉取通讯录部门与成员，并成功通过 `OrganizationService` 和 `IdentityManager` 落盘入库，且能在 `mdm_identities` 中正确记录 `source_system='wecom'`。
  - `No-Go`: 遇到了无法绕过且未记录在案的微信 API 限流、死锁或模型强校验报错。

## 3. 架构设计蓝图 (Architecture Blueprint)

### 3.1 目录结构
```text
devops_collector/plugins/wecom/
    ├── __init__.py        # 插件注册 (PluginRegistry.register_worker)
    ├── client.py          # WeComClient (处理 AccessToken 缓存与刷新)
    └── worker.py          # WeComWorker (执行采集并落库)
```

### 3.2 核心实施路径 (Implementation Path)

**阶段 1: 客户端对接 (WeComClient)**
- 实现 Access Token 获取机制 (附带缓存管理，失效重刷)。
- 实现 `get_departments()`：拉取全量部门树。
- 实现 `get_department_users(dept_id)`：拉取部门下所有成员（包含详情）。

**阶段 2: 数据暂存落盘 (Staging & Worker)**
- 在 `WeComWorker` 中，利用刚才更新的 `save_to_staging` 和 `bulk_save_to_staging` 指令，将所有从 API 获取的用户、部门 Raw JSON 落库至 `mdm_staging`。

**阶段 3: 主数据入库逻辑 (MDM UPSERT)**
严格遵循 "contexts.md 17.2 节" 的规范：
1. **部门集成**：直接调用 `self.org_service.upsert_organization()`。
    - *关键参数*：`manager_raw_id = dept['department_leader']` (延迟对齐，不再递归)。
    - *来源参数*：`source = "wecom"` (透传血缘)。
2. **人员集成**：使用 `IdentityManager.get_or_create_user()`。
    - 外部系统源必须是 `"wecom"`，传入 `wecom_userid` (即 `userid`) 作为唯一标识，并带上邮箱和工号供 `IdentityManager` 去执行存量身份匹配对齐。

## 4. 关键风险与应对策略 (Risks & Mitigations)

| 风险区 | 触发场景 | 防御预案 |
| :--- | :--- | :--- |
| **API 限流** | 递归拉取人员详情过快导致 429。 | Client 层实现自动 Backoff (退避重试)。|
| **循环引用死锁** | 部门负责人 A 不在库，且 A 所在的部门也刚开始建。| 已经通过 `manager_raw_id` 物理隔离，**防线已就位**。 |
| **主键冲突** | 原先库里只有 `zhangsan` 的邮件，但由于没有全局锁产生高并发创建。| `IdentityManager` 内置了 `begin_nested()` 防雷并发操作拦截。 |
| **全量拉取过载** | 几万人的企业通讯录拉取造成内存崩盘。| 按组织层级结构进行分治抓取 (yield per page) ，并分批 Flush。 |

## 5. 预期结果与下一步 (Next Step)
完成骨架和 API Client 后，我们将针对上述的蓝图编写核心业务测试进行单体联调验证。
建议下发指令：`请开始构建 WeCom 插件骨架` 启动开发。

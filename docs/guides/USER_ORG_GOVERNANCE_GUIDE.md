# 用户、组织与身份治理部署与同步指南

本文档旨在说明 DevOps 系统中“用户与组织模块”的架构设计、数据同步流程以及身份对齐治理的操作规范。

## 1. 架构设计：双轨制组织与身份增强

本系统采用 **“金数据只读，业务层增强”** 的设计理念，将组织架构分为两个维度：

- **行政组织 (Administrative Org)**：同步自 HR 系统，用于行政管理、部门效能统计和人力成本核算。在本系统中对应的表为 `mdm_organizations`。
- **虚拟团队 (Virtual Team)**：由业务管理员自行组建，用于项目攻坚、敏捷开发迭代。支持跨部门成员组合，支持投入百分比（Allocation Ratio）。

## 2. 数据同步流程 (Data Synchronization)

### 2.1 HR 数据导入 (MDM Layer)

- **核心逻辑**：通过 ETL 任务或集成脚本，定期将 HR 系统的员工与组织存入 `mdm_identities` 与 `mdm_organizations`。
- **版本控制**：采用 SCD Type 2 (慢变维) 策略。当员工调岗或更名时，系统会自动保留历史版本，并标记最新的记录为 `is_current = True`。

### 2.2 外部帐号发现 (Discovery Layer)

- **触发机制**：当 GitLab, Jira 或 SonarQube 同步任务运行时，会自动发现新的外部 UserID 或 Email。
- **默认操作**：系统会尝试按 Email 自动关联 MDM 用户。如果关联失败，会创建一条状态为 `PENDING` 的 `mdm_identity_mappings` 记录。

## 3. 身份治理操作 (Identity Governance)

### 3.1 自动对齐引擎

在完成基础数据同步后，建议运行身份治理脚本，以提高帐号匹配的置信度。

**运行脚本：**

```powershell
# 1. 测试运行 (Dry Run)，查看匹配建议
python scripts/run_identity_resolver.py

# 2. 正式应用匹配结果
python scripts/run_identity_resolver.py --apply
```

- **置信度评分**：脚本根据 Email 相似度、姓名拼写、工号前缀计算 0-1 之间的分值。
- **状态流转**：
  - 分数 > 0.9：标记为 `VERIFIED`（已核实）。
  - 分数 0.6-0.9：标记为 `AUTO`（算法匹配，需人工确认）。

### 3.2 人工复核

管理员可通过管理后台（Admin UI）查看所有标记为 `AUTO` 或 `PENDING` 的映射关系。

- API 端点：`PATCH /admin/identity-mappings/{id}/status`
- 操作：点击“核实”将状态转为 `VERIFIED`。

## 4. 业务团队管理 (Team Management)

### 4.1 组建虚拟项目团队

在完成身份对齐后，管理员可以开始组建业务维度的虚拟组织。

1. **创建团队**：通过 `/admin/teams` 接口定义团队名称与所属行政层级（仅挂载参考）。
2. **添加成员**：指定 `user_id`、`role_code` (LEADER/MEMBER) 以及 `allocation_ratio` (0.0-1.0)。

### 4.2 应用场景

- **看板过滤**：选择“虚拟团队A”，系统将自动根据团队成员绑定的各系统账号，聚合其在 GitLab/Jira 上的所有活动轨迹。
- **效能度量**：在计算团队速率或产出时，系统会自动按 `allocation_ratio` 排除成员在其他团队的投入干扰。

## 5. 部署预查清单 (Checklist)

1. **数据库迁移**：确保运行了最新的 SQL 脚本，包含 `sys_teams` 和 `sys_team_members` 表。
2. **配置文件 (config.ini)**：
   - 检查 `DB_URI` 是否正确指向 PostgreSQL 实例。
   - 配置内部域名后缀，以提高 `IdentityResolver` 的匹配准确度。
3. **环境变量**：确保 `GITLAB_PRIVATE_TOKEN` 具有足够的权限访问用户列表，以执行外部账号发现。

---
*本文档由 Antigravity AI 生成，用于指导 DevOps 系统的身份与组织治理工作。*

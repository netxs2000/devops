# 内控与合规性洞察体系

## 概述

本文档详细说明了基于现有元数据构建的七大内控与合规性洞察模型，旨在帮助企业满足 SOX 404、ISO 27001、ITIL、GDPR/PIPL 等合规框架要求，降低内控风险和法律风险。

---

## 1. 四眼原则合规性监控 (Four-Eyes Principle Compliance)

### 核心问题
代码合并是否经过独立审查？是否存在"自己审自己"的风险？

### 合规框架
- ✅ **SOX 404**: 职责分离（Segregation of Duties）
- ✅ **ISO 27001**: 访问控制（Access Control）

### 数据链路
- `merge_requests.author_id` vs `notes.author_id` (评审人)
- `merge_requests.approval_count`

### 核心指标
- **自审率 (Self-Review Rate)**: 作者 = 审批人的 MR 占比
- **单人审批率**: 仅 1 人审批的 MR 占比
- **零审批率**: 无任何审批直接合并的 MR 占比
- **合规率**: ≥2 人独立审批的 MR 占比

### 预警阈值
| 指标 | 绿线 (Compliant) | 黄线 (Warning) | 红线 (Critical) |
|:---|:---|:---|:---|
| 零审批率 | < 5% | 5% - 20% | > 20% |
| 合规率 | > 80% | 50% - 80% | < 50% |

### 管理价值
- ✅ 满足 SOX 404 内控要求（职责分离）
- ✅ 降低代码质量风险
- ✅ 为审计提供合规证据

### SQL 视图
`view_compliance_four_eyes_principle` (位于 `devops_collector/sql/COMPLIANCE_ANALYTICS.sql`)

---

## 2. 权限滥用与异常操作检测 (Privilege Abuse Detection)

### 核心问题
是否存在权限滥用？谁在非工作时间进行敏感操作？

### 合规框架
- ✅ **SOX 404**: 访问控制
- ✅ **ISO 27001**: 9.2 访问控制、9.4 系统和应用访问控制
- ✅ **GDPR/PIPL**: 数据访问审计

### 数据链路
- `commits.is_off_hours` (加班提交标识)
- `deployments.created_at` (部署时间)
- `gitlab_group_members.access_level` (权限级别)

### 核心指标
- **非工作时间部署率**: 22:00-08:00 或周末的生产部署占比
- **超级管理员操作频率**: Owner/Maintainer 级别的直接操作频次
- **跨权限操作**: 普通开发者执行了需要更高权限的操作

### 预警阈值
| 指标 | 低风险 | 中风险 | 高风险 |
|:---|:---|:---|:---|
| 非工作时间部署率 | < 10% | 10% - 30% | > 30% |

### 管理价值
- ✅ 识别内部威胁（Insider Threat）
- ✅ 满足 ISO 27001 访问控制要求
- ✅ 预防数据泄露风险

### SQL 视图
`view_compliance_privilege_abuse` (位于 `devops_collector/sql/COMPLIANCE_ANALYTICS.sql`)

---

## 3. 变更管理合规性追溯 (Change Management Traceability)

### 核心问题
生产变更是否有完整的审批链？是否可追溯到需求？

### 合规框架
- ✅ **SOX 404**: 变更管理
- ✅ **ISO 27001**: 12.1 操作程序和职责、14.2 变更管理
- ✅ **ITIL**: 变更管理流程

### 数据链路
- `deployments` → `merge_requests` → `issues` → `jira_issues`
- `traceability_links` (跨系统追溯)

### 核心指标
- **变更可追溯率**: 生产部署能追溯到 Jira 需求的占比
- **紧急变更率**: 标记为"hotfix"的生产部署占比
- **未授权变更**: 无对应 Issue/Ticket 的部署占比

### 预警阈值
| 指标 | 合规 | 部分合规 | 不合规 |
|:---|:---|:---|:---|
| 可追溯率 | > 90% | 70% - 90% | < 70% |
| 未授权变更率 | < 5% | 5% - 20% | > 20% |

### 管理价值
- ✅ 满足 ITIL 变更管理要求
- ✅ 为事故调查提供审计线索
- ✅ 降低合规风险

### SQL 视图
`view_compliance_change_traceability` (位于 `devops_collector/sql/COMPLIANCE_ANALYTICS.sql`)

---

## 4. 敏感数据访问审计 (Sensitive Data Access Audit)

### 核心问题
谁在访问敏感代码？是否存在未授权访问？

### 合规框架
- ✅ **ISO 27001**: 9.4 系统和应用访问控制
- ✅ **GDPR**: Article 32 数据处理安全
- ✅ **PIPL**: 第 51 条 数据安全保护义务

### 数据链路
- `commits` (涉及敏感文件的提交)
- `commit_file_stats.file_path` (文件路径模式匹配)
- `notes` (敏感 Issue 的评论)

### 敏感文件模式
- `config/`, `secret/`, `credential/`, `password/`
- `.env`, `key`, `token`, `cert`

### 核心指标
- **敏感文件变更频率**: 涉及敏感路径的提交频次
- **跨部门访问**: 非项目成员访问敏感项目的记录
- **密钥泄露风险**: 提交中包含疑似密钥的模式匹配

### 风险等级
| 等级 | 条件 |
|:---|:---|
| 高风险 | 敏感文件提交 > 10 次/90天 |
| 中风险 | 敏感文件提交 3-10 次/90天 |
| 低风险 | 敏感文件提交 1-3 次/90天 |

### 管理价值
- ✅ 满足 GDPR/PIPL 数据保护要求
- ✅ 预防密钥泄露事故
- ✅ 为安全审计提供证据

### SQL 视图
`view_compliance_sensitive_data_access` (位于 `devops_collector/sql/COMPLIANCE_ANALYTICS.sql`)

---

## 5. 职责分离有效性验证 (Segregation of Duties - SoD)

### 核心问题
同一人是否同时拥有"开发"和"发布"权限？

### 合规框架
- ✅ **SOX 404**: 职责分离（核心要求）
- ✅ **ISO 27001**: 6.1.2 职责分离

### 数据链路
- `commits.gitlab_user_id` (开发者)
- `deployments.deployer_id` (部署者)
- `gitlab_group_members.access_level`

### SoD 违规场景
1. **Dev + Deploy**: 同一人既提交代码又执行生产部署
2. **Dev + Admin**: 开发者同时拥有超级管理员权限
3. **关键岗位兼任**: 同一人同时担任 Dev + DBA + Ops

### 核心指标
- **SoD 违规率**: 违反职责分离原则的用户占比
- **权限集中度**: 单一账号拥有的高危权限数量

### 风险等级
| 等级 | 违规类型 |
|:---|:---|
| Critical | Dev + Deploy (同一人开发并部署) |
| Medium | Dev + Admin (开发者拥有管理员权限) |
| Low | 合规 |

### 管理价值
- ✅ 满足 SOX 404 职责分离要求
- ✅ 降低舞弊风险
- ✅ 为内审提供合规证据

### SQL 视图
`view_compliance_segregation_of_duties` (位于 `devops_collector/sql/COMPLIANCE_ANALYTICS.sql`)

---

## 6. 开源许可证合规性扫描 (Open Source License Compliance)

### 核心问题
使用的开源组件是否存在许可证冲突？

### 法律风险
- ❌ **GPL/AGPL**: 传染性许可证，可能导致商业软件被迫开源
- ⚠️ **LGPL**: 动态链接可接受，静态链接有风险
- ✅ **Apache/MIT**: 商业友好型许可证

### 数据链路
- `gitlab_dependencies.name` + `gitlab_dependencies.version`
- 外部 API 查询许可证信息（如 SPDX、ClearlyDefined）

### 核心指标
- **高风险许可证占比**: GPL/AGPL 等传染性许可证的使用比例
- **未知许可证组件**: 无法识别许可证的依赖数量
- **许可证冲突**: 商业项目中使用 GPL 组件的情况

### 风险等级
| 等级 | 条件 |
|:---|:---|
| Critical | 检测到 AGPL 许可证 |
| High | GPL 许可证 > 5 个 |
| Warning | 未知许可证 > 30% |
| Low | 仅使用 Apache/MIT 等商业友好许可证 |

### 管理价值
- ✅ 降低知识产权诉讼风险
- ✅ 满足企业开源治理政策
- ✅ 为法务部门提供风险清单

### SQL 视图
`view_compliance_oss_license_risk` (位于 `devops_collector/sql/COMPLIANCE_ANALYTICS.sql`)

---

## 7. 代码归属与知识产权保护 (Code Ownership & IP Protection)

### 核心问题
代码是否被离职员工带走？是否存在未授权的代码复制？

### 法律风险
- ❌ **商业秘密泄露**: 核心代码被带到竞争对手公司
- ❌ **知识产权侵权**: 员工将公司代码用于个人项目

### 数据链路
- `commits.author_email` vs `users.state` (离职员工)
- `commit_file_stats` (代码变更模式)

### 异常行为模式
1. **离职前异常提交**: 员工离职前 30 天的提交量激增
2. **大规模代码删除**: 单次提交删除超过 1000 行
3. **外部邮箱提交**: 使用非企业邮箱的提交

### 核心指标
- **离职前活跃度**: 离职前 30 天提交量 / 过去 90 天提交量
- **大规模删除次数**: 单次删除 > 1000 行的提交数
- **外部邮箱提交数**: 使用非企业邮箱的提交数

### 风险等级
| 等级 | 条件 |
|:---|:---|
| Critical | 离职员工在离职前 30 天提交量 > 50% 总量 |
| High | 大规模删除 > 3 次 |
| Medium | 外部邮箱提交 > 5 次 |

### 管理价值
- ✅ 预防知识产权流失
- ✅ 识别潜在的数据窃取行为
- ✅ 为法律诉讼提供证据

### SQL 视图
`view_compliance_ip_protection` (位于 `devops_collector/sql/COMPLIANCE_ANALYTICS.sql`)

---

## 合规框架映射表

| 洞察模型 | SOX 404 | ISO 27001 | ITIL | GDPR/PIPL | 法律风险 |
|:---|:---:|:---:|:---:|:---:|:---:|
| 四眼原则 | ✅ | ✅ | - | - | 低 |
| 权限滥用 | ✅ | ✅ | - | ✅ | 中 |
| 变更管理 | ✅ | ✅ | ✅ | - | 中 |
| 敏感数据 | - | ✅ | - | ✅ | 高 |
| 职责分离 | ✅ | ✅ | - | - | 中 |
| 开源许可 | - | - | - | - | 高 |
| IP 保护 | - | ✅ | - | - | 极高 |

---

## 实施建议

### 数据准备
1. **配置敏感文件模式**: 在系统中维护敏感文件路径的正则表达式
2. **标记离职员工**: 及时更新 `users.state` 为 `inactive`
3. **记录部署者信息**: 确保 `deployments` 表包含部署者 ID
4. **集成许可证 API**: 对接 SPDX 或 ClearlyDefined API 获取准确的许可证信息

### 使用场景
- **季度内审**: 使用所有视图生成合规报告
- **年度外审**: 为审计师提供四眼原则、职责分离、变更管理的证据
- **安全事件调查**: 使用权限滥用、敏感数据访问视图追溯异常行为
- **法律诉讼**: 使用 IP 保护视图提供员工窃取代码的证据

### 预警机制
建议将以下场景接入实时预警（企业微信/钉钉）：
- ✅ SoD 违规：新增 Dev + Deploy 权限的用户
- ✅ 敏感数据访问：单日敏感文件提交 > 5 次
- ✅ IP 风险：离职员工在离职前 7 天内有大规模提交
- ✅ 许可证风险：新增 GPL/AGPL 依赖

---

## 附录：合规术语对照表

| 术语 | 英文 | 说明 |
|:---|:---|:---|
| 四眼原则 | Four-Eyes Principle | 重要操作需要两人独立审批 |
| 职责分离 | Segregation of Duties (SoD) | 同一人不能同时拥有冲突的权限 |
| 内部威胁 | Insider Threat | 来自组织内部的安全威胁 |
| 传染性许可证 | Copyleft License | 如 GPL，要求衍生作品也开源 |
| 商业秘密 | Trade Secret | 受法律保护的非公开商业信息 |
| SOX 404 | Sarbanes-Oxley Act Section 404 | 美国上市公司内控法案 |
| ISO 27001 | Information Security Management | 信息安全管理体系国际标准 |
| ITIL | IT Infrastructure Library | IT 服务管理最佳实践框架 |
| GDPR | General Data Protection Regulation | 欧盟通用数据保护条例 |
| PIPL | Personal Information Protection Law | 中国个人信息保护法 |

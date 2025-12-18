# Issue 标签强制规范实施指南

> **创建日期**: 2025-12-17  
> **实施方案**: 方案 A - Issue 模板优化 + 标签检查脚本

---

## 📋 概述

本方案通过**软性提醒 + 定期检查**的方式，确保团队成员正确标记 Issue，提高数据质量。

### 核心组件

1. **优化的 Bug 报告模板** (`.gitlab/issue_templates/Bug.md`)
   - 醒目的必填标签提示
   - 清晰的标签选择指南
   - 提交前检查清单

2. **标签完整性检查工具** (`scripts/check_issue_labels.py`)
   - 自动检查 Issue 标签完整性
   - 自动添加 `needs-labels` 标签
   - 自动评论提醒
   - 生成数据质量报告

---

## 🎯 必要标签定义

### Bug 类型 Issue 必须包含

| 维度 | 必选标签 | 说明 |
|------|---------|------|
| **类型** | `type::bug` | 标识为 Bug |
| **严重程度** | `severity::S1/S2/S3/S4` | 4 选 1 |
| **优先级** | `priority::P0/P1/P2/P3` | 4 选 1 |
| **Bug 类别** | `bug-category::*` | 9 选 1 |
| **Bug 来源** | `bug-source::production/non-production` | 2 选 1，用于统计缺陷逃逸率 |

### Feature 类型 Issue 必须包含

| 维度 | 必选标签 | 说明 |
|------|---------|------|
| **类型** | `type::feature` | 标识为功能需求 |
| **优先级** | `priority::P0/P1/P2/P3` | 4 选 1 |

---

---

## 🏛️ 需求全生命周期协作规范

为了确保需求质量，所有 `type::requirement` 议题必须遵循以下闭环流程。

### 1. 流程阶段详解

| 阶段 | 状态标签 | 动作说明 | 关键操作 |
|------|---------|---------|---------|
| **起草** | `status::draft` | PM 编写需求背景、描述及验收标准 (AC) | 默认模板自动生成 |
| **提交** | `status::reviewing` | PM 确认编写完成，指派评审人并开启评审 | 评论 `/label ~"status::reviewing"` |
| **评审** | `status::reviewing` | 评审人勾选要点，并在评论区给出结论指令 | 使用下方的结论指令字典 |
| **修正** | `status::feedback` | 评审未通过，PM 按意见修改需求 | 评论 `/label ~"status::reviewing"` 重新提交 |
| **准入** | `status::todo` | 评审通过，进入待开发队列 | 指令自动流转 |
| **交付** | `status::done` | 开发/测试完成，需求正式结项 | 评论 `/label ~"resolution::done" /close` |

### 2. 评审结论指令字典 (Quick Actions)

评审人在核对完需求描述中的 checklist 后，请直接在议题评论区回复以下指令：

*   **✅ 准入通过**: 
    ` /label ~"review-result::approved" ~"status::todo"`
*   **⚠️ 需修正**: 
    `/label ~"review-result::rework" ~"status::feedback"`
*   **❌ 驳回/不做**: 
    `/label ~"review-result::rejected" /close`

### 3. 关闭原因指令字典

关闭任何议题时（需求或缺陷），请务必带上原因标签：

*   **已完成**: `/label ~"resolution::done" /close`
*   **重复**: `/label ~"resolution::duplicate" /close`
*   **延期**: `/label ~"resolution::postponed" /close`
*   **不做**: `/label ~"resolution::wontfix" /close`
*   **设计如此**: `/label ~"resolution::by_design" /close`
*   **无法重现 (仅 Bug)**: `/label ~"resolution::cannot_reproduce" /close`
*   **转为需求 (仅 Bug)**: `/label ~"resolution::as_requirement" /close`

---

## 💻 代码评审 (Code Review) 协作规范

为提升代码质量，所有合并请求 (MR) 必须经过至少一名非作者成员的评审。

### 1. 提交人 (Author) 职责
- **DoD 自检**: 必须勾选 MR 描述中的自检清单（代码风格、单元测试、安全审计）。
- **最小变更**: 每个 MR 建议控制在 300 行代码以内，以便深度评审。
- **紧急说明**: 如需加急，请手动添加 `review::speed-up` 标签。

### 2. 评审人 (Reviewer) 职责
- **反应时间**: 收到评审请求后，原则上需在 24 小时内给出首轮反馈。
- **建设性意见**: 避免只指出错误，应给出具体的重构建议。
- **打分制 (可选)**: 可以在评论区通过评论 `/label` 确认结果。

### 3. MR 结论指令字典 (Quick Actions)

评审完成后，请在 MR 下方发表评论：

*   **✅ 允许合并 (Approved)**: 
    `/label ~"review-result::approved" /approve`
*   **⚠️ 需要调整 (Rework)**: 
    `/label ~"review-result::rework" ~"review::ping-pong"`
*   **❌ 拒绝 (Rejected)**: 
    `/label ~"review-result::rejected" /close`

---

## 🚀 使用指南

### 1. 创建 Bug 时

#### Step 1: 选择 Bug 模板

在 GitLab 创建 Issue 时，选择 "Bug" 模板。

#### Step 2: 填写 Bug 信息

按照模板提示填写：
- Bug 描述
- 复现步骤
- 环境信息

#### Step 3: 选择必要标签

**⚠️ 重要**: 必须选择以下 5 个维度的标签：

1. **严重程度** (Severity): 
   - [ ] `severity::S1` - 致命
   - [ ] `severity::S2` - 严重
   - [ ] `severity::S3` - 一般
   - [ ] `severity::S4` - 轻微

2. **优先级** (Priority):
   - [ ] `priority::P0` - 紧急
   - [ ] `priority::P1` - 高
   - [ ] `priority::P2` - 中
   - [ ] `priority::P3` - 低

3. **Bug 类别** (Bug Category):
   - [ ] `bug-category::code-error` - 代码错误
   - [ ] `bug-category::configuration` - 配置相关
   - [ ] `bug-category::performance` - 性能问题
   - [ ] `bug-category::security` - 安全相关
   - [ ] ... (其他 5 种)


5. **Bug 来源** (Bug Source):
   - [ ] `bug-source::production` - 生产环境发现
   - [ ] `bug-source::non-production` - 非生产环境发现

#### Step 4: 设置标题

标题格式: `[P?][S?][类别] 简短描述`

示例:
```
[P0][S1][代码错误] 空指针异常导致服务崩溃
[P1][S2][性能] 查询响应时间超过 5 秒
[P2][S3][配置] 数据库连接池配置不当
```

#### Step 5: 提交前检查

使用模板底部的检查清单确认所有必要标签已选择。

---

### 2. 定期标签检查

#### 手动检查

```bash
# 检查所有打开的 Issue
python scripts/check_issue_labels.py --project-id <your_project_id>

# 检查所有 Issue（包括已关闭）
python scripts/check_issue_labels.py --project-id <your_project_id> --state all

# 生成 CSV 报告
python scripts/check_issue_labels.py --project-id <your_project_id> --output report.csv
```

#### 自动处理

```bash
# 自动为标签不完整的 Issue 添加 needs-labels 标签
python scripts/check_issue_labels.py --project-id <your_project_id> --auto-label

# 自动添加提醒评论
python scripts/check_issue_labels.py --project-id <your_project_id> --auto-comment

# 同时添加标签和评论
python scripts/check_issue_labels.py --project-id <your_project_id> --auto-label --auto-comment
```

#### 定期任务（推荐）

**Windows (任务计划程序)**:
```powershell
# 每天上午 9:00 运行检查
schtasks /create /tn "GitLab Issue Label Check" /tr "python C:\path\to\scripts\check_issue_labels.py --project-id 123 --auto-label --auto-comment" /sc daily /st 09:00
```

**Linux (Crontab)**:
```bash
# 每天上午 9:00 运行检查
0 9 * * * cd /path/to/project && python scripts/check_issue_labels.py --project-id 123 --auto-label --auto-comment
```

---

## 📊 检查报告示例

### 控制台输出

```
================================================================================
标签完整性检查报告
================================================================================
总 Issue 数: 50
标签完整: 42
标签不完整: 8
完整率: 84.0%
================================================================================

标签不完整的 Issue 列表:

Issue #123: 登录页面无法访问
  类型: bug
  缺少标签: severity, bug_category
  链接: https://gitlab.example.com/project/issues/123

Issue #124: 优化查询性能
  类型: feature
  缺少标签: priority
  链接: https://gitlab.example.com/project/issues/124
```

### CSV 报告

| Issue ID | Issue IID | 标题 | 状态 | 类型 | 缺少标签 | 链接 |
|---------|----------|------|------|------|---------|------|
| 1001 | 123 | 登录页面无法访问 | opened | bug | severity, bug_category | https://... |
| 1002 | 124 | 优化查询性能 | opened | feature | priority | https://... |

---

## 🔔 自动提醒机制

### needs-labels 标签

标签不完整的 Issue 会被自动添加 `needs-labels` 标签，便于：
- 在看板中过滤显示
- 设置通知规则
- 统计数据质量

### 自动评论

检查工具会自动在 Issue 中添加评论：

```
⚠️ **标签不完整提醒**

此 Issue 缺少以下必要标签：
- ❌ **severity**
- ❌ **bug_category**

请及时补充标签，以便正确分类和处理。

**必要标签说明**:
- **severity**: 严重程度 (S1/S2/S3/S4) - 仅 Bug
- **priority**: 优先级 (P0/P1/P2/P3)
- **bug_category**: Bug 类别 (9 种分类) - 仅 Bug
- **bug_source**: Bug 来源 (production/non-production) - 仅 Bug，用于统计缺陷逃逸率

---
*此评论由标签检查工具自动生成*
```

---

## 📈 数据质量监控

### 每周数据质量报告

建议每周生成一次数据质量报告：

```bash
# 生成本周报告
python scripts/check_issue_labels.py \
  --project-id <your_project_id> \
  --state all \
  --output "reports/label_quality_$(date +%Y%m%d).csv"
```

### 关键指标

- **标签完整率**: 标签完整的 Issue / 总 Issue 数
- **平均补充时间**: 从创建到补充完整标签的平均时间
- **高频缺失标签**: 最常缺失的标签类别

---

## 💡 最佳实践

### 1. 团队培训

- 在团队会议上介绍标签规范
- 分享 Bug 报告模板的使用方法
- 说明标签对数据分析的重要性

### 2. 及时反馈

- 发现标签不完整时，及时通知创建者
- 定期在团队会议上通报数据质量情况

### 3. 持续改进

- 根据团队反馈优化标签体系
- 定期审查标签使用情况
- 调整必要标签定义

### 4. 激励机制

- 表扬标签使用规范的团队成员
- 在团队看板上展示数据质量指标
- 将标签完整率纳入团队 KPI

---

## 🔧 故障排查

### 问题 1: 检查脚本运行失败

**原因**: 缺少依赖或配置错误

**解决方案**:
```bash
# 检查 config.ini 配置
cat config.ini

# 确认 GitLab URL 和 Token 正确
python -c "from devops_collector.core.config import Config; print(Config.GITLAB_URL)"
```

### 问题 2: 无法添加标签或评论

**原因**: Token 权限不足

**解决方案**:
- 确保 Personal Access Token 具有 `api` 权限
- 确认对项目有 Developer 或更高权限

### 问题 3: 检查结果不准确

**原因**: 标签定义不匹配

**解决方案**:
- 检查 `check_issue_labels.py` 中的 `REQUIRED_LABELS` 定义
- 确认与实际创建的标签名称一致

---

## 📚 相关文档

- [GitLab 需求管理与测试管理基础数据源](./GITLAB_METRICS_DATA_SOURCES.md)
- [GitLab Issue 分类与标记规范指南](./GITLAB_ISSUE_CLASSIFICATION_GUIDE.md)
- [GitLab 标签批量创建工具](./scripts/create_gitlab_labels.py)

---

## 📝 更新日志

### 2025-12-17
- ✅ 创建优化的 Bug 报告模板
- ✅ 创建标签完整性检查工具
- ✅ 创建使用指南文档

---

**文档维护**: 本文档应随团队实践演进而持续更新。

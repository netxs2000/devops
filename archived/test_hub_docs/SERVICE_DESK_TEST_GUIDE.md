# Service Desk 功能测试指南

## 快速开始

### 1. 启动服务

```bash
2. 检查文件：`devops_portal/service_desk_tickets.json`
python main.py
```

服务启动后会自动加载历史工单数据。

---

## 2. 访问前端界面

### 主页
http://localhost:8000/static/service_desk.html

### Bug 提交
http://localhost:8000/static/service_desk_bug.html

### 需求提交
http://localhost:8000/static/service_desk_requirement.html

### 工单追踪
http://localhost:8000/static/service_desk_track.html

---

## 3. 手动测试流程

### 测试 1: 提交 Bug

1. 打开 Bug 提交页面
2. 填写表单：
   - 姓名：张三
   - 邮箱：zhangsan@example.com
   - 项目 ID：1（根据实际修改）
   - 标题：登录页面无法显示
   - 严重程度：S2
   - 优先级：P2
   - 环境：production
   - 复现步骤、实际结果、期望结果
3. 点击提交
4. 记录追踪码（例如：BUG-20251227-001）

### 测试 2: 提交需求

1. 打开需求提交页面
2. 填写表单：
   - 姓名：李四
   - 邮箱：lisi@example.com
   - 项目 ID：1
   - 标题：增加数据导出功能
   - 需求类型：feature
   - 详细描述
3. 点击提交
4. 记录追踪码（例如：REQ-20251227-001）

### 测试 3: 追踪工单

1. 打开工单追踪页面
2. 输入之前获得的追踪码
3. 点击查询
4. 查看工单详情和状态
5. 点击 GitLab 链接验证 Issue 创建成功

---

## 4. API 测试（使用 curl 或 Postman）

### 提交 Bug

```bash
curl -X POST "http://localhost:8000/service-desk/submit-bug?project_id=1" \
  -H "Content-Type: application/json" \
  -d "{\"requester_name\":\"测试用户\",\"requester_email\":\"test@example.com\",\"title\":\"测试Bug\",\"severity\":\"S2\",\"priority\":\"P2\",\"province\":\"nationwide\",\"environment\":\"test\",\"steps_to_repro\":\"测试步骤\",\"actual_result\":\"实际结果\",\"expected_result\":\"期望结果\"}"
```

### 查询工单

```bash
curl http://localhost:8000/service-desk/track/BUG-20251227-001
```

### 获取工单列表

```bash
curl http://localhost:8000/service-desk/tickets
```

---

## 5. 验证数据持久化

1. 提交几个工单
2. 检查文件：`test_hub/service_desk_tickets.json`
3. 重启服务
4. 访问工单列表，确认数据未丢失

---

## 6. 验证 GitLab 集成

1. 提交工单后，登录 GitLab
2. 进入对应项目的 Issues 页面
3. 查找带 `[Service Desk]` 前缀的 Issue
4. 验证标签：
   - Bug: `type::bug`, `severity::S2`, `origin::service-desk`
   - 需求: `type::requirement`, `req-type::feature`, `origin::service-desk`

---

## 常见问题

### Q: 提交失败，提示 "无效的严重程度"
A: 严重程度必须是 S0, S1, S2, S3 之一

### Q: 提交失败，提示 "无效的环境"
A: 环境必须是 production, staging, test, development 之一

### Q: 追踪码查询不到工单
A: 检查追踪码格式是否正确（BUG-YYYYMMDD-XXX 或 REQ-YYYYMMDD-XXX）

### Q: GitLab Issue 未创建
A: 检查 config.ini 中的 GitLab URL 和 Token 配置

---

## 功能清单

- [x] Bug 提交表单
- [x] 需求提交表单
- [x] 工单追踪查询
- [x] 工单列表展示
- [x] 数据持久化（JSON）
- [x] GitLab Issue 自动创建
- [x] 参数验证
- [x] 状态同步
- [x] 响应式设计
- [x] 错误处理

---

## 下一步优化（可选）

1. 邮件通知功能
2. 附件上传支持
3. 工单评论功能
4. 统计报表
5. 权限管理

---

**完成时间**: 2025-12-27  
**状态**: ✅ 已完成

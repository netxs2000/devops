# API 接口参考文档 (API Reference)

**版本**: 4.1.0
**日期**: 2026-01-11

本文档提供 DevOps Data Application Platform 的 RESTful API 接口参考。

> **在线文档**: 系统运行后，可访问 `http://localhost:8000/docs` 获取 Swagger UI 交互式文档。

---

## 目录

1. [认证接口 (Authentication)](#1-认证接口-authentication)
2. [服务台接口 (Service Desk)](#2-服务台接口-service-desk)
3. [测试管理接口 (Test Management)](#3-测试管理接口-test-management)
4. [迭代计划接口 (Iteration Plan)](#4-迭代计划接口-iteration-plan)
5. [质量分析接口 (Quality Analytics)](#5-质量分析接口-quality-analytics)
6. [DevEx 脉搏接口 (DevEx Pulse)](#6-devex-脉搏接口-devex-pulse)
7. [管理接口 (Admin)](#7-管理接口-admin)
8. [通用响应格式](#8-通用响应格式)
9. [错误代码](#9-错误代码)

---

## 1. 认证接口 (Authentication)

**基础路径**: `/auth`

### 1.1 用户注册

注册新用户账号。

```http
POST /auth/register
```

**请求体**:

```json
{
  "email": "user@example.com",
  "password": "your_password",
  "full_name": "张三"
}
```

**响应**:

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "张三",
  "is_active": true
}
```

---

### 1.2 用户登录

获取 JWT 访问令牌。

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded
```

**请求体**:

```text
username=user@example.com&password=your_password
```

**响应**:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### 1.3 获取当前用户

获取当前登录用户信息。

```http
GET /auth/me
Authorization: Bearer <token>
```

**响应**:

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "张三",
  "department_id": "dept_001",
  "gitlab_connected": true,
  "is_active": true
}
```

---

### 1.4 GitLab OAuth 绑定

发起 GitLab 账号绑定流程。

```http
GET /auth/gitlab/bind
Authorization: Bearer <token>
```

**响应**: 302 重定向至 GitLab 授权页面

---

### 1.5 GitLab OAuth 回调

GitLab 授权完成后的回调处理。

```http
GET /auth/gitlab/callback?code={code}&state={state}
```

**响应**: 302 重定向至前端页面

---

## 2. 服务台接口 (Service Desk)

**基础路径**: `/service-desk`

### 2.1 获取业务项目列表

获取当前用户可访问的业务项目。

```http
GET /service-desk/business-projects
Authorization: Bearer <token>
```

**响应**:

```json
[
  {
    "id": "proj_001",
    "name": "电商平台",
    "description": "主营业务电商系统"
  }
]
```

---

### 2.2 提交缺陷

通过服务台提交缺陷反馈。

```http
POST /service-desk/submit-bug?mdm_id={project_id}
Authorization: Bearer <token>
```

**请求体**:

```json
{
  "title": "订单支付失败",
  "actual_result": "点击支付按钮后页面无响应",
  "attachments": ["![screenshot](/uploads/xxx.png)"]
}
```

**响应**:

```json
{
  "status": "success",
  "tracking_code": "BUG-123",
  "message": "缺陷已提交至统一受理仓，等待研发分拣！"
}
```

---

### 2.3 提交需求

通过服务台提交业务需求。

```http
POST /service-desk/submit-requirement?mdm_id={project_id}
Authorization: Bearer <token>
```

**请求体**:

```json
{
  "title": "新增会员积分功能",
  "description": "用户购买商品后可获得积分，积分可兑换优惠券",
  "attachments": []
}
```

**响应**:

```json
{
  "status": "success",
  "tracking_code": "REQ-456",
  "message": "需求已提报至受理中心，等待研发规划！"
}
```

---

### 2.4 获取工单列表

获取当前用户可见的工单列表。

```http
GET /service-desk/tickets
Authorization: Bearer <token>
```

**响应**:

```json
[
  {
    "id": 123,
    "title": "订单支付失败",
    "status": "open",
    "issue_type": "bug",
    "origin_dept_name": "销售部",
    "target_dept_name": "技术部",
    "created_at": "2026-01-11T10:30:00"
  }
]
```

---

### 2.5 查询工单状态

根据工单 ID 查询详细状态。

```http
GET /service-desk/track/{ticket_id}
```

---

### 2.6 获取我的工单

获取当前用户创建的所有工单。

```http
GET /service-desk/my-tickets
Authorization: Bearer <token>
```

---

### 2.7 更新工单状态

更新指定工单的状态。

```http
PATCH /service-desk/tickets/{ticket_id}/status
Authorization: Bearer <token>
```

**请求体**:

```json
{
  "new_status": "resolved"
}
```

---

### 2.8 拒绝工单

RD 拒绝并关闭工单。

```http
POST /service-desk/tickets/{iid}/reject
Authorization: Bearer <token>
```

**请求体**:

```json
{
  "project_id": 123,
  "reason": "该问题为已知行为，非缺陷"
}
```

---

## 3. 测试管理接口 (Test Management)

**基础路径**: `/projects/{project_id}`

### 3.1 测试用例

#### 获取测试用例列表

```http
GET /projects/{project_id}/test-cases
Authorization: Bearer <token>
```

#### 创建测试用例

```http
POST /projects/{project_id}/test-cases
Authorization: Bearer <token>
```

**权限要求**: `maintainer` 或 `admin`

**请求体**:

```json
{
  "title": "验证用户登录功能",
  "preconditions": "用户已注册",
  "steps": [
    {"step": 1, "action": "输入用户名密码", "expected": "输入框正常显示"},
    {"step": 2, "action": "点击登录", "expected": "跳转至首页"}
  ],
  "priority": "P1",
  "test_type": "功能测试"
}
```

#### 批量导入测试用例

```http
POST /projects/{project_id}/test-cases/import
Content-Type: multipart/form-data
Authorization: Bearer <token>
```

**权限要求**: `maintainer` 或 `admin`

#### 克隆测试用例

```http
POST /projects/{project_id}/test-cases/clone?source_project_id={id}
Authorization: Bearer <token>
```

---

### 3.2 执行测试

```http
POST /projects/{project_id}/test-cases/{issue_iid}/execute?result={passed|failed|blocked}
Authorization: Bearer <token>
```

**权限要求**: `tester`、`maintainer` 或 `admin`

**响应**:

```json
{
  "status": "success",
  "execution_id": 789,
  "result": "passed"
}
```

---

### 3.3 需求管理

#### 获取需求列表

```http
GET /projects/{project_id}/requirements
Authorization: Bearer <token>
```

#### 创建需求

```http
POST /projects/{project_id}/requirements
Authorization: Bearer <token>
```

#### 获取需求详情

```http
GET /projects/{project_id}/requirements/{iid}
Authorization: Bearer <token>
```

#### 更新需求评审状态

```http
PUT /projects/{project_id}/requirements/{iid}/review-state?review_state={approved|rejected|pending}
Authorization: Bearer <token>
```

---

### 3.4 缺陷管理

#### 获取缺陷列表

```http
GET /projects/{project_id}/bugs
```

#### 创建缺陷

```http
POST /projects/{project_id}/defects
Authorization: Bearer <token>
```

---

### 3.5 AI 辅助功能

#### 根据 AC 生成测试步骤

```http
POST /projects/{project_id}/generate-steps?requirement_iid={iid}
Authorization: Bearer <token>
```

#### 根据需求生成测试用例

```http
POST /projects/{project_id}/requirements/{iid}/generate-test-case
Authorization: Bearer <token>
```

#### 根据描述生成测试步骤

```http
POST /projects/{project_id}/generate-steps-from-description
Authorization: Bearer <token>
```

**请求体**:

```json
{
  "description": "用户可以通过手机号注册账号，需验证短信验证码"
}
```

#### 生成自动化测试代码

```http
POST /projects/{project_id}/test-cases/{iid}/generate-code
Authorization: Bearer <token>
```

#### 重复工单检测

```http
GET /projects/{project_id}/scan-duplicates?type={requirement|bug}
Authorization: Bearer <token>
```

#### 缺陷根因分析

```http
POST /projects/{project_id}/defects/{iid}/rca
```

---

### 3.6 报告导出

#### 导出需求跟踪矩阵 (RTM)

```http
GET /projects/{project_id}/export-rtm
Authorization: Bearer <token>
```

**响应类型**: `text/markdown`

---

## 4. 迭代计划接口 (Iteration Plan)

**基础路径**: `/iteration-plan`

### 4.1 获取迭代列表

```http
GET /iteration-plan/milestones?project_id={id}
Authorization: Bearer <token>
```

### 4.2 获取迭代详情

```http
GET /iteration-plan/milestones/{milestone_id}?project_id={id}
Authorization: Bearer <token>
```

### 4.3 获取迭代任务

```http
GET /iteration-plan/milestones/{milestone_id}/issues?project_id={id}
Authorization: Bearer <token>
```

---

## 5. 质量分析接口 (Quality Analytics)

**基础路径**: `/quality`

### 5.1 获取省份质量数据

```http
GET /quality/provinces
Authorization: Bearer <token>
```

### 5.2 获取省份对标数据

```http
GET /quality/benchmarking
Authorization: Bearer <token>
```

---

## 6. DevEx 脉搏接口 (DevEx Pulse)

**基础路径**: `/devex-pulse`

### 6.1 提交心情指数

```http
POST /devex-pulse/feedback
Authorization: Bearer <token>
```

**请求体**:

```json
{
  "satisfaction_score": 4,
  "feedback_text": "今天完成了一个重要功能，感觉不错",
  "blockers": "无"
}
```

### 6.2 获取团队心情趋势

```http
GET /devex-pulse/trends?days=30
Authorization: Bearer <token>
```

---

## 7. 管理接口 (Admin)

**基础路径**: `/admin`

### 7.1 项目管理

```http
GET /admin/projects
POST /admin/projects
PUT /admin/projects/{id}
DELETE /admin/projects/{id}
```

### 7.2 用户管理

```http
GET /admin/users
PUT /admin/users/{id}/role
```

### 7.3 部门管理

```http
GET /admin/departments
POST /admin/departments
```

---

## 8. 通用响应格式

### 成功响应

```json
{
  "status": "success",
  "data": { ... },
  "message": "操作成功"
}
```

### 分页响应

```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

---

## 9. 错误代码

| HTTP 状态码 | 错误类型 | 说明 |
| :--- | :--- | :--- |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或 Token 过期 |
| 403 | Forbidden | 无权限访问资源 |
| 404 | Not Found | 资源不存在 |
| 422 | Validation Error | 请求体校验失败 |
| 500 | Internal Server Error | 服务器内部错误 |

### 错误响应示例

```json
{
  "detail": "Email already registered"
}
```

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 认证说明

除明确标注为公开接口外，所有接口均需要在请求头中携带 JWT Token:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Token 有效期默认为 24 小时。如需调整，请修改 `.env` 中的 `JWT_EXPIRATION_HOURS` 配置。

---

## 更多信息

* **Swagger UI**: `http://localhost:8000/docs`
* **ReDoc**: `http://localhost:8000/redoc`
* **OpenAPI JSON**: `http://localhost:8000/openapi.json`
